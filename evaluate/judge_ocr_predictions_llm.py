import argparse
import ast
import concurrent.futures as futures
import json
import os
from pathlib import Path
import sys
import time

import requests


PROMPT_VERSION = "dev_ocr_judge_v4"
DEFAULT_URL = "http://127.0.0.1:3000/v1/chat/completions"
DEFAULT_MODEL = "deepseek-v4-flash"
USABILITY_SCORE_THRESHOLD = 75
USABILITY_NOISE_THRESHOLD = 6
COMPLETION_NOISE_THRESHOLD = 1

SYSTEM_PROMPT = """你是开发场景 OCR 评测裁判。只比较人工真值 label 与模型预测 prediction，判断 prediction 是否忠实还原、是否不影响开发者使用。

只输出 JSON，不要输出 Markdown、解释性正文或思考过程。

核心原则：
1. 还原优先：label 是唯一基准。不要根据常识、代码语义或图片想象补全 label 中没有的内容。
2. 使用影响：重点判断差异是否影响复制运行、搜索定位、阅读理解、配置/命令执行或错误排查。
3. 开发风险：关键符号、标识符、大小写、数字、路径、括号、引号、缩进、块顺序和错误信息错误，应明显扣分。
4. 生成污染：不要奖励额外解释、总结、推断、代码改写、格式美化、思考过程或 Markdown 包裹。
5. 内容改写：擅自增删、补全或重写可执行代码、配置、命令是较大问题；注释或非执行说明的少量增删相对更轻，按是否误导理解扣分。

允许轻微无害差异：首尾空白、少量空行、不会影响阅读的分隔线差异、非代码 UI 区域轻微换序。不要使用 NED 或字符编辑距离思路打分。"""

USER_PROMPT_TEMPLATE = """请比较 OCR 真值和模型预测，并按规则输出裁判 JSON。

评分步骤：
1. 判断 prediction 是否忠实还原 label 的文字、符号、缩进、结构和顺序。
2. 判断差异是否影响开发者复制运行、搜索定位、阅读理解、配置/命令执行或排查问题。
3. 分别给六个 0-10 原始子项分。轻微且不影响使用的格式差异轻扣；影响代码/命令/配置语义、擅自增删/补全/重写可执行内容、解释、幻觉、重复等必须重扣。
4. 给 subjective_adjustment_m5_p4。大多数样本为 0；只在六维分无法表达整体观感时小幅修正。

六个评分维度：
- content_coverage_0_10：主要内容覆盖。关注主体代码、配置、终端、错误信息、文件名、关键上下文是否保留；边缘 UI 小遗漏不要重扣。
- symbol_accuracy_0_10：字符与符号准确性。重点看括号、引号、反斜杠、连字符、下划线、冒号、分号、运算符、路径、版本号、数字、大小写和标识符。
- indentation_alignment_0_10：缩进与对齐。Python、YAML、Markdown、表格、树形结构等缩进敏感内容要严格；普通段落空格差异可轻扣。
- structure_format_0_10：结构格式。关注换行、代码块边界、列表项、表格列、错误堆栈行、代码围栏和区域分隔是否被破坏。
- reading_region_order_0_10：阅读顺序与区域顺序。代码、配置、终端、错误列表、补全框顺序要严格；非代码 UI 区域轻微换序且不影响理解时可轻扣或不扣。
- noise_and_usability_0_10：噪声控制与开发可用性。衡量重复、幻觉、无关文本、解释性文字、交付外包装，以及 prediction 是否可直接给开发者使用。

score_0_100 是六项等权折算展示分，不代表最终 benchmark 权重；最终加权、阈值和惩罚由 benchmark v3 单独计算。
subjective_adjustment_m5_p4 范围为 -5 到 4，默认 0：
- 六维分已充分反映问题时，不要重复扣分。
- 整体可用性明显低于六维分反映时，给 -1 到 -5。
- prediction 有形式差异但实际很可用，且六维分可能低估时，给 +1 到 +4。

总分锚点：
- 90-100：几乎可直接使用，只存在极少无害差异。
- 75-89：主体正确，少量字符或格式问题，人工很容易修复。
- 60-74：可读但需要明显人工修正，复制代码或命令有风险。
- 40-59：只保留部分有效内容，只能参考。
- 0-39：严重漏识别、错读、重复、幻觉、拒答，或主要不是 OCR。

硬性扣分与封顶：
- 主要是在解释/总结图片，而不是 OCR 转写：noise_and_usability_0_10 <= 4，score_0_100 <= 60。
- 大部分内容与 label 无关、严重幻觉、输出思考过程或模板性说明：noise_and_usability_0_10 <= 3，score_0_100 <= 40。
- 空输出、极短输出或只有“无法识别”等拒答：score_0_100 <= 5。
- 长输出重复发散：noise_and_usability_0_10 <= 2，score_0_100 通常 <= 55，并标记 repeated_output。
- 正确 OCR 外加入长段解释、推理过程、改写说明、Markdown 说明或“下面是识别结果”等交付外文本：明显扣 noise_and_usability_0_10，并标记 explanatory_text 或 extra_wrapper_text。
- 擅自新增、删除、补全、重写可执行代码、配置或命令，或把 OCR 改写成“更合理”的代码：标记 code_added_removed_or_rewritten；明显扣 content_coverage_0_10、symbol_accuracy_0_10、noise_and_usability_0_10；score_0_100 通常 <= 70，严重时 <= 55。
- 只涉及注释或非执行说明的少量增删：标记 comment_added_removed；轻到中度扣 content_coverage_0_10 或 noise_and_usability_0_10。若改变理解、隐藏警告或引入误导，可按较严重问题处理。
- 用 Markdown 代码围栏包裹纯 OCR 且 label 没有围栏：轻扣 noise 与 structure；若加入语言名、说明、行号或改写，明显扣分。
- 关键符号错误会影响复制运行：symbol_accuracy_0_10 <= 7；大量关键符号错误时 <= 5。
- 缩进层级明显错误且影响语义：indentation_alignment_0_10 <= 6；大面积丢失时 <= 4。
- 代码块、配置块、终端输出或错误列表顺序明显错乱：reading_region_order_0_10 <= 6。非代码 UI 区域换序但不影响阅读理解时不要重扣。
- 主体内容覆盖不足一半：content_coverage_0_10 <= 5，score_0_100 通常 <= 65。
- prediction 比 label 多出大量无关文本时，不能只按覆盖率给高分；必须扣 noise_and_usability_0_10 及相关结构/顺序分。

错误标签只能从下列集合中选择，允许多选：
missing_major_text, wrong_code_symbol, wrong_identifier_or_keyword, wrong_number_or_path,
bad_line_break_or_indent, broken_structure, wrong_reading_order, wrong_region_order,
extra_ui_text, explanatory_text, extra_wrapper_text, hallucinated_text, repeated_output,
truncated_output, empty_or_too_short, refusal_or_unrecognized, over_cleaned_or_rewritten,
code_added_removed_or_rewritten, comment_added_removed, mostly_correct, needs_human_review

请输出如下 JSON：
{{
  "score_0_100": 0,
  "grade": "A|B|C|D|E",
  "dimension_scores": {{
    "content_coverage_0_10": 0,
    "symbol_accuracy_0_10": 0,
    "indentation_alignment_0_10": 0,
    "structure_format_0_10": 0,
    "reading_region_order_0_10": 0,
    "noise_and_usability_0_10": 0
  }},
  "subjective_adjustment_m5_p4": 0,
  "error_tags": [],
  "needs_human_review": false,
  "brief_reason": "不超过80字"
}}

样本 ID：
{id}

人工真值 label：
<<<LABEL
{label}
LABEL

模型预测 prediction：
<<<PREDICTION
{prediction}
PREDICTION"""


def read_token_from_file(path: Path, variable_name: str):
    if not path or not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(variable_name) and "=" in line:
            _, value = line.split("=", 1)
            try:
                parsed = ast.literal_eval(value.strip())
            except (SyntaxError, ValueError):
                parsed = value.strip().strip("\"'")
            if isinstance(parsed, str) and parsed:
                return parsed
    return None


def load_api_key(args):
    if args.api_key:
        return args.api_key
    if args.api_key_env and os.environ.get(args.api_key_env):
        return os.environ[args.api_key_env]
    token = read_token_from_file(args.api_key_file, args.api_key_env)
    if token:
        return token
    raise SystemExit(f"No API key found. Set {args.api_key_env} or pass --api-key.")


def load_done(path: Path):
    done = {}
    if not path.exists():
        return done
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(f"warning: ignored invalid JSON on {path}:{line_number}", file=sys.stderr)
                continue
            image = record.get("image")
            if image:
                done[image] = record
    return done


def load_records(path: Path):
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            record.setdefault("index", line_number)
            records.append(record)
    return records


def extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def normalize_grade(score):
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "E"


def validate_judgement(data):
    dims = data.get("dimension_scores") or {}
    keys = {
        "content_coverage_0_10": 10,
        "symbol_accuracy_0_10": 10,
        "indentation_alignment_0_10": 10,
        "structure_format_0_10": 10,
        "reading_region_order_0_10": 10,
        "noise_and_usability_0_10": 10,
    }
    legacy_aliases = {
        "content_coverage_0_10": ("content_coverage_0_30", 30),
        "symbol_accuracy_0_10": ("symbol_accuracy_0_25", 25),
        "structure_format_0_10": ("structure_format_0_5", 5),
        "noise_and_usability_0_10": ("noise_and_usability_0_20", 20),
    }
    normalized_dims = {
        key: max(0, min(max_score, int(dims.get(key, 0))))
        for key, max_score in keys.items()
    }
    for key, (old_key, old_max) in legacy_aliases.items():
        if normalized_dims[key] == 0 and old_key in dims:
            normalized_dims[key] = max(0, min(10, round(float(dims.get(old_key, 0)) / old_max * 10)))
    data["dimension_scores"] = normalized_dims
    score = round(sum(normalized_dims.values()) / len(normalized_dims) * 10)
    data["score_0_100"] = score
    data["subjective_adjustment_m5_p4"] = max(
        -5.0,
        min(4.0, float(data.get("subjective_adjustment_m5_p4", data.get("subjective_adjustment", 0)) or 0)),
    )
    data["grade"] = normalize_grade(data["score_0_100"])
    data["error_tags"] = sorted(
        {
            str(tag).strip()
            for tag in (data.get("error_tags") or [])
            if str(tag).strip()
        }
    )
    if data["score_0_100"] >= 85 and not data["error_tags"]:
        data["error_tags"] = ["mostly_correct"]
    data["needs_human_review"] = bool(data.get("needs_human_review", False))
    data["brief_reason"] = str(data.get("brief_reason", ""))[:120]
    return data


def call_judge(record, api_key, args):
    sample_id = record.get("id") or Path(record.get("image", f"sample_{record['index']}")).stem
    prompt = USER_PROMPT_TEMPLATE.format(
        id=sample_id,
        label=record.get("label", ""),
        prediction=record.get("prediction", ""),
    )
    payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    if args.temperature is not None:
        payload["temperature"] = args.temperature
    if args.max_tokens:
        payload["max_tokens"] = args.max_tokens
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    response = None
    last_error = None
    for attempt in range(args.retries + 1):
        try:
            response = requests.post(args.url, headers=headers, json=payload, timeout=args.timeout)
            if response.status_code != 429:
                break
            last_error = RuntimeError(f"HTTP 429: {response.text[:500]}")
        except requests.RequestException as exc:
            response = None
            last_error = exc
        if attempt < args.retries:
            delay = args.retry_sleep_seconds * (2**attempt)
            print(f"  retry in {delay:.1f}s", flush=True)
            time.sleep(delay)
    if response is None:
        raise RuntimeError(f"request failed: {last_error}")
    if response.status_code != 200:
        raise RuntimeError(f"request failed: HTTP {response.status_code}: {response.text[:800]}")
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return validate_judgement(extract_json(content))


def write_jsonl(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        handle.flush()


def trimmed_mean(values):
    if not values:
        return None
    if len(values) <= 2:
        return sum(values) / len(values)
    ordered = sorted(values)
    trimmed = ordered[1:-1]
    return sum(trimmed) / len(trimmed)


def write_summary(path: Path, output_path: Path, model: str, source_path: Path):
    records = list(load_done(output_path).values())
    scores = [record["score_0_100"] for record in records]
    noise_scores = []
    subjective_adjustments = []
    grades = {}
    tags = {}
    for record in records:
        grades[record["grade"]] = grades.get(record["grade"], 0) + 1
        dims = record.get("dimension_scores") or {}
        noise_scores.append(int(dims.get("noise_and_usability_0_10", dims.get("noise_and_usability_0_20", 0))))
        subjective_adjustments.append(
            max(
                -5.0,
                min(4.0, float(record.get("subjective_adjustment_m5_p4", record.get("subjective_adjustment", 0)) or 0)),
            )
        )
        for tag in record.get("error_tags", []):
            tags[tag] = tags.get(tag, 0) + 1
    summary = {
        "judge_model": model,
        "judge_prompt_version": PROMPT_VERSION,
        "source": str(source_path),
        "samples": len(records),
        "avg_llm_score": sum(scores) / len(scores) if scores else None,
        "trimmed_avg_llm_score": trimmed_mean(scores),
        "trimmed_avg_rule": "drop one highest score and one lowest score when samples > 2",
        "best_score": max(scores) if scores else None,
        "worst_score": min(scores) if scores else None,
        "grade_distribution": grades,
        "avg_noise_and_usability_score": sum(noise_scores) / len(noise_scores) if noise_scores else None,
        "avg_noise_and_usability_max_score": 10,
        "avg_subjective_adjustment_m5_p4": (
            sum(subjective_adjustments) / len(subjective_adjustments) if subjective_adjustments else None
        ),
        "subjective_adjustment_rule": "per-sample subjective_adjustment_m5_p4, default 0, range [-5, 4]",
        "effective_completion_rule": f"noise_and_usability_0_10 > {COMPLETION_NOISE_THRESHOLD}",
        "effective_completion_count_noise_gt_1": sum(
            1 for score in noise_scores if score > COMPLETION_NOISE_THRESHOLD
        ),
        "effective_completion_rate_over_scored_records": (
            sum(1 for score in noise_scores if score > COMPLETION_NOISE_THRESHOLD) / len(records)
            if records
            else None
        ),
        "usable_rule": (
            f"score_0_100 > {USABILITY_SCORE_THRESHOLD} and "
            f"noise_and_usability_0_10 > {USABILITY_NOISE_THRESHOLD}"
        ),
        "usable_rate_score_gt_75_noise_gt_6": (
            sum(
                1
                for record in records
                if record["score_0_100"] > USABILITY_SCORE_THRESHOLD
                and int(
                    (record.get("dimension_scores") or {}).get(
                        "noise_and_usability_0_10",
                        (record.get("dimension_scores") or {}).get("noise_and_usability_0_20", 0),
                    )
                )
                > USABILITY_NOISE_THRESHOLD
            )
            / len(records)
            if records
            else None
        ),
        "usable_rate_score_ge_75": sum(1 for score in scores if score >= 75) / len(scores) if scores else None,
        "severe_badcase_rate_score_lt_40": sum(1 for score in scores if score < 40) / len(scores) if scores else None,
        "needs_human_review_count": sum(1 for record in records if record.get("needs_human_review")),
        "top_error_tags": sorted(tags.items(), key=lambda item: item[1], reverse=True)[:20],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="Judge OCR predictions with an OpenAI-compatible LLM.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--errors", type=Path, required=True)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--api-key")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=800)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-sleep-seconds", type=float, default=5.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def judge_one(record, api_key, args):
    judgement = call_judge(record, api_key, args)
    payload = {
        "image": record.get("image"),
        "source_model": record.get("model"),
        "ned": record.get("ned"),
        "label_chars": record.get("label_chars"),
        "prediction_chars": record.get("prediction_chars"),
        **judgement,
        "judge_model": args.model,
        "judge_prompt_version": PROMPT_VERSION,
    }
    return payload


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    api_key = load_api_key(args)
    records = load_records(args.input)
    if args.limit is not None:
        records = records[: args.limit]
    done = load_done(args.output)
    pending = [record for record in records if record.get("image") not in done]
    print(f"samples={len(records)} done={len(done)} pending={len(pending)} workers={args.workers} model={args.model}", flush=True)
    if args.workers <= 1:
        for offset, record in enumerate(pending, start=1):
            image = record.get("image")
            print(f"[{offset}/{len(pending)}] {image}", flush=True)
            try:
                payload = judge_one(record, api_key, args)
                write_jsonl(args.output, payload)
                done[image] = payload
                print(f"  score={payload['score_0_100']} grade={payload['grade']} tags={','.join(payload['error_tags'])}", flush=True)
            except Exception as exc:
                write_jsonl(args.errors, {"image": image, "error": str(exc), "judge_model": args.model})
                print(f"  error: {exc}", file=sys.stderr, flush=True)
    else:
        with futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_record = {executor.submit(judge_one, record, api_key, args): record for record in pending}
            for offset, future in enumerate(futures.as_completed(future_to_record), start=1):
                record = future_to_record[future]
                image = record.get("image")
                try:
                    payload = future.result()
                    write_jsonl(args.output, payload)
                    done[image] = payload
                    print(
                        f"[{offset}/{len(pending)}] {image} score={payload['score_0_100']} grade={payload['grade']} tags={','.join(payload['error_tags'])}",
                        flush=True,
                    )
                except Exception as exc:
                    write_jsonl(args.errors, {"image": image, "error": str(exc), "judge_model": args.model})
                    print(f"[{offset}/{len(pending)}] {image} error: {exc}", file=sys.stderr, flush=True)
    summary = write_summary(args.summary, args.output, args.model, args.input)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
