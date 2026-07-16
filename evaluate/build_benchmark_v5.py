from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path


CATEGORY_WEIGHTS = {
    "P01": 0.15,
    "P02": 0.08,
    "P03": 0.15,
    "P04": 0.12,
    "P05": 0.10,
    "P06": 0.08,
    "P07": 0.12,
    "P08": 0.08,
    "P09": 0.12,
}

SIMPLE_PENALTY_CAP = 20.0
MEDIUM_RISK_PENALTY_CAP = 5.0
HARD_RISK_PENALTY_CAP = 10.0

DIMENSION_WEIGHTS = {
    "content_coverage_0_10": 0.18,
    "symbol_accuracy_0_10": 0.24,
    "indentation_alignment_0_10": 0.16,
    "structure_format_0_10": 0.16,
    "reading_region_order_0_10": 0.10,
    "noise_and_usability_0_10": 0.16,
}

CATEGORY_NAMES = {
    "P01": "代码编辑器主体",
    "P02": "终端与命令行",
    "P03": "报错诊断与日志",
    "P04": "配置与工程声明",
    "P05": "版本控制与代码审阅",
    "P06": "文档与网页代码块",
    "P07": "API 参考与表格化结构",
    "P08": "交互式开发工具视图",
    "P09": "多区域混合开发屏",
}


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_number}") from exc
    return rows


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    path.write_text(text + ("\n" if text else ""), encoding="utf-8")


def norm_image_key(value: str | None) -> str:
    if not value:
        return ""
    key = value.replace("\\", "/")
    if key.startswith("./"):
        key = key[2:]
    for prefix in ("测试集/", "code_ocr_eval_dataset_v3/"):
        if key.startswith(prefix):
            key = key[len(prefix) :]
    return key


def sample_score(dims: dict) -> float:
    total = 0.0
    for key, weight in DIMENSION_WEIGHTS.items():
        value = max(0.0, min(10.0, float(dims.get(key, 0) or 0))) / 10.0
        total += weight * (value**1.35)
    return 100.0 * total


def is_severe(row: dict) -> bool:
    dims = row.get("dimension_scores") or {}
    tags = set(row.get("error_tags") or [])
    label_chars = int(row.get("label_chars") or 0)
    prediction_chars = int(row.get("prediction_chars") or 0)
    output_too_long = label_chars > 0 and prediction_chars > 3 * label_chars
    return (
        bool(row.get("missing_record"))
        or float(dims.get("noise_and_usability_0_10") or 0) <= 1
        or float(dims.get("content_coverage_0_10") or 0) <= 2
        or float(dims.get("symbol_accuracy_0_10") or 0) <= 2
        or float(dims.get("structure_format_0_10") or 0) <= 2
        or "code_added_removed_or_rewritten" in tags
        or "hallucinated_text" in tags
        or "empty_or_too_short" in tags
        or "refusal_or_unrecognized" in tags
        or "repeated_output" in tags
        or (output_too_long and float(dims.get("noise_and_usability_0_10") or 0) <= 4)
    )


def is_effectively_complete(row: dict) -> bool:
    dims = row.get("dimension_scores") or {}
    return not row.get("missing_record") and float(dims.get("noise_and_usability_0_10") or 0) > 1


def is_direct_usable(row: dict) -> bool:
    dims = row.get("dimension_scores") or {}
    return (
        not row.get("missing_record")
        and float(dims.get("content_coverage_0_10") or 0) >= 8
        and float(dims.get("symbol_accuracy_0_10") or 0) >= 8
        and float(dims.get("structure_format_0_10") or 0) >= 7
        and float(dims.get("noise_and_usability_0_10") or 0) > 6
    )


def has_any_tag(row: dict, tags: set[str]) -> bool:
    return bool(tags.intersection(set(row.get("error_tags") or [])))


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def pct(numerator: int, denominator: int) -> float | None:
    return numerator / denominator * 100 if denominator else None


def ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def rounded(value: float | None, digits: int = 4) -> float | None:
    return round(value, digits) if value is not None else None


def load_manifest(path: Path) -> tuple[list[dict], dict[str, dict]]:
    rows = read_jsonl(path)
    by_image = {}
    for row in rows:
        image_key = norm_image_key(row.get("image"))
        by_image[image_key] = row
    return rows, by_image


def build_rows(manifest_rows: list[dict], manifest_by_image: dict[str, dict], predictions: list[dict], judgements: list[dict]) -> list[dict]:
    predictions_by_image = {norm_image_key(row.get("image")): row for row in predictions}
    judgements_by_image = {norm_image_key(row.get("image")): row for row in judgements}
    rows = []
    for meta in manifest_rows:
        image_key = norm_image_key(meta.get("image"))
        prediction = predictions_by_image.get(image_key, {})
        judgement = judgements_by_image.get(image_key)
        if judgement is None:
            row = {
                "id": meta.get("id"),
                "image": image_key,
                "primary_category": meta.get("primary_category"),
                "primary_category_name": meta.get("primary_category_name") or CATEGORY_NAMES.get(meta.get("primary_category")),
                "difficulty_level": meta.get("difficulty_level"),
                "missing_record": True,
                "sample_score_v5": 0.0,
                "score_0_100": 0,
                "dimension_scores": {},
                "error_tags": ["missing_record"],
                "label_chars": prediction.get("label_chars"),
                "prediction_chars": prediction.get("prediction_chars"),
                "ned": prediction.get("ned"),
            }
        else:
            dims = judgement.get("dimension_scores") or {}
            row = {
                **judgement,
                "id": meta.get("id"),
                "image": image_key,
                "primary_category": meta.get("primary_category"),
                "primary_category_name": meta.get("primary_category_name") or CATEGORY_NAMES.get(meta.get("primary_category")),
                "difficulty_level": meta.get("difficulty_level"),
                "missing_record": False,
                "label_chars": judgement.get("label_chars", prediction.get("label_chars")),
                "prediction_chars": judgement.get("prediction_chars", prediction.get("prediction_chars")),
                "ned": prediction.get("ned", judgement.get("ned")),
                "sample_score_v5": sample_score(dims),
            }
        row["severe_badcase_v5"] = is_severe(row)
        rows.append(row)
    extra_images = sorted(set(judgements_by_image) - set(manifest_by_image))
    for image_key in extra_images:
        row = dict(judgements_by_image[image_key])
        row["image"] = image_key
        row["extra_record_not_in_manifest"] = True
        row["sample_score_v5"] = sample_score(row.get("dimension_scores") or {})
        row["severe_badcase_v5"] = is_severe(row)
        rows.append(row)
    return rows


def aggregate(
    rows: list[dict],
    total_manifest: int,
    run_name: str,
    prompt_group: str,
    predictions_path: Path,
    judge_path: Path,
    dataset_version: str,
    content_version: str,
    dataset_revision: str | None,
) -> dict:
    scored_rows = [row for row in rows if not row.get("extra_record_not_in_manifest")]
    present_rows = [row for row in scored_rows if not row.get("missing_record")]
    scores = [float(row.get("sample_score_v5") or 0) for row in present_rows]

    by_category = defaultdict(list)
    by_difficulty = defaultdict(list)
    severe_by_category = Counter()
    severe_by_difficulty = Counter()
    count_by_category = Counter()
    count_by_difficulty = Counter()
    tags = Counter()
    neds = []
    direct_usable = 0
    simple_direct_usable = 0
    completion = 0

    for row in scored_rows:
        category = row.get("primary_category") or "unknown"
        difficulty = row.get("difficulty_level") or "unknown"
        count_by_category[category] += 1
        count_by_difficulty[difficulty] += 1
        if not row.get("missing_record"):
            by_category[category].append(float(row.get("sample_score_v5") or 0))
            by_difficulty[difficulty].append(float(row.get("sample_score_v5") or 0))
            if is_direct_usable(row):
                direct_usable += 1
                if difficulty == "simple":
                    simple_direct_usable += 1
            if is_effectively_complete(row):
                completion += 1
            if isinstance(row.get("ned"), (int, float)):
                neds.append(float(row["ned"]))
        if row.get("severe_badcase_v5"):
            severe_by_category[category] += 1
            severe_by_difficulty[difficulty] += 1
        for tag in row.get("error_tags") or []:
            tags[str(tag)] += 1

    category_scores = {
        key: {
            "name": CATEGORY_NAMES.get(key, key),
            "count": count_by_category.get(key, 0),
            "scored": len(by_category.get(key, [])),
            "score": rounded(mean(by_category.get(key, []))),
            "severe_rate_pct": rounded(pct(severe_by_category.get(key, 0), count_by_category.get(key, 0))),
        }
        for key in CATEGORY_WEIGHTS
    }
    difficulty_scores = {
        key: {
            "count": count_by_difficulty.get(key, 0),
            "scored": len(by_difficulty.get(key, [])),
            "score": rounded(mean(by_difficulty.get(key, []))),
            "severe_rate_pct": rounded(pct(severe_by_difficulty.get(key, 0), count_by_difficulty.get(key, 0))),
        }
        for key in ("simple", "medium", "hard")
    }

    category_weighted = sum(CATEGORY_WEIGHTS[key] * (category_scores[key]["score"] or 0) for key in CATEGORY_WEIGHTS)
    simple_total = count_by_difficulty.get("simple", 0)
    medium_total = count_by_difficulty.get("medium", 0)
    hard_total = count_by_difficulty.get("hard", 0)
    simple_direct_usable_rate = ratio(simple_direct_usable, simple_total)
    medium_severe_rate_ratio = ratio(severe_by_difficulty.get("medium", 0), medium_total)
    hard_severe_rate_ratio = ratio(severe_by_difficulty.get("hard", 0), hard_total)
    simple_penalty = min(SIMPLE_PENALTY_CAP, SIMPLE_PENALTY_CAP * (1.0 - simple_direct_usable_rate))
    medium_risk_penalty = min(MEDIUM_RISK_PENALTY_CAP, MEDIUM_RISK_PENALTY_CAP * medium_severe_rate_ratio)
    hard_risk_penalty = min(HARD_RISK_PENALTY_CAP, HARD_RISK_PENALTY_CAP * hard_severe_rate_ratio)
    difficulty_risk_penalty = medium_risk_penalty + hard_risk_penalty
    global_mean = mean(scores) or 0.0

    severe_count = sum(1 for row in scored_rows if row.get("severe_badcase_v5"))
    missing_count = sum(1 for row in scored_rows if row.get("missing_record"))
    code_rewrite_count = tags.get("code_added_removed_or_rewritten", 0)
    hallucination_or_explanation_count = (
        tags.get("hallucinated_text", 0) + tags.get("explanatory_text", 0) + tags.get("extra_wrapper_text", 0)
    )
    severe_rate = pct(severe_count, total_manifest) or 0.0
    missing_rate = pct(missing_count, total_manifest) or 0.0
    code_rewrite_rate = pct(code_rewrite_count, total_manifest) or 0.0
    hallucination_or_explanation_rate = pct(hallucination_or_explanation_count, total_manifest) or 0.0
    reliability_penalty = min(
        15.0,
        0.12 * severe_rate
        + 0.20 * missing_rate
        + 0.08 * code_rewrite_rate
        + 0.06 * hallucination_or_explanation_rate,
    )
    raw_score = category_weighted - simple_penalty - difficulty_risk_penalty
    final_score = max(0.0, min(100.0, raw_score - reliability_penalty))

    weakest_category = min(
        CATEGORY_WEIGHTS,
        key=lambda key: category_scores[key]["score"] if category_scores[key]["score"] is not None else -1,
    )
    weakest_difficulty = min(
        ("simple", "medium", "hard"),
        key=lambda key: difficulty_scores[key]["score"] if difficulty_scores[key]["score"] is not None else -1,
    )
    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "run_name": run_name,
        "prompt_group": prompt_group,
        "benchmark_family": "v5",
        "content_version": content_version,
        "dataset_revision": dataset_revision,
        "dataset_version": dataset_version,
        "dataset_id": dataset_version,
        "total_manifest_records": total_manifest,
        "scored_records": len(present_rows),
        "missing_records": missing_count,
        "predictions_path": str(predictions_path),
        "judge_path": str(judge_path),
        "final_score_v5": rounded(final_score),
        "raw_score_v5": rounded(raw_score),
        "category_weighted_score_v5": rounded(category_weighted),
        "simple_direct_usable_count": simple_direct_usable,
        "simple_direct_usable_rate_pct": rounded(simple_direct_usable_rate * 100),
        "simple_penalty_v5": rounded(simple_penalty),
        "medium_severe_rate_pct": rounded(medium_severe_rate_ratio * 100),
        "medium_risk_penalty_v5": rounded(medium_risk_penalty),
        "hard_severe_rate_pct": rounded(hard_severe_rate_ratio * 100),
        "hard_risk_penalty_v5": rounded(hard_risk_penalty),
        "difficulty_risk_penalty_v5": rounded(difficulty_risk_penalty),
        "formula_v5": "category_weighted_score_v5 - simple_penalty_v5 - difficulty_risk_penalty_v5 - reliability_penalty_v5",
        "global_sample_mean_score_v5": rounded(global_mean),
        "global_sample_mean_usage_v5": "diagnostic_only",
        "reliability_penalty_v5": rounded(reliability_penalty),
        "severe_rate_pct": rounded(severe_rate),
        "missing_record_rate_pct": rounded(missing_rate),
        "code_rewrite_rate_pct": rounded(code_rewrite_rate),
        "hallucination_or_explanation_rate_pct": rounded(hallucination_or_explanation_rate),
        "direct_usable_rate_pct": rounded(pct(direct_usable, total_manifest)),
        "completion_rate_pct": rounded(pct(completion, total_manifest)),
        "safety_score_pct": rounded(100.0 - severe_rate),
        "avg_ned": rounded(mean(neds)),
        "weakest_category": weakest_category,
        "weakest_category_name": CATEGORY_NAMES.get(weakest_category),
        "weakest_difficulty": weakest_difficulty,
        "category_scores": category_scores,
        "difficulty_scores": difficulty_scores,
        "top_error_tags": tags.most_common(30),
    }


def markdown_report(summary: dict) -> str:
    category_rows = "\n".join(
        f"| {key} {value['name']} | {value['count']} | {value['scored']} | {value['score'] if value['score'] is not None else '-'} | {value['severe_rate_pct'] if value['severe_rate_pct'] is not None else '-'}% |"
        for key, value in summary["category_scores"].items()
    )
    difficulty_rows = "\n".join(
        f"| {key} | {value['count']} | {value['scored']} | {value['score'] if value['score'] is not None else '-'} | {value['severe_rate_pct'] if value['severe_rate_pct'] is not None else '-'}% |"
        for key, value in summary["difficulty_scores"].items()
    )
    tags = "\n".join(f"| {tag} | {count} |" for tag, count in summary.get("top_error_tags", [])[:15]) or "| - | - |"
    return f"""# {summary['run_name']} OCR Benchmark v5 测评报告

更新时间：{summary['created_at']}

## 基本信息

| 项 | 值 |
| --- | --- |
| run | {summary['run_name']} |
| benchmark | v5（内容版本 {summary['content_version']}） |
| prompt group | {summary['prompt_group']} |
| 数据集 | {summary['dataset_version']} |
| 记录 | {summary['scored_records']} / {summary['total_manifest_records']} |
| predictions | `{summary['predictions_path']}` |
| judge | `{summary['judge_path']}` |

## 榜单指标

| 指标 | 值 |
| --- | ---: |
| final_score_v5 | {summary['final_score_v5']} |
| raw_score_v5 | {summary['raw_score_v5']} |
| category_weighted_score_v5 | {summary['category_weighted_score_v5']} |
| simple_direct_usable_rate_pct | {summary['simple_direct_usable_rate_pct']} |
| simple_penalty_v5 | -{summary['simple_penalty_v5']} |
| medium_severe_rate_pct | {summary['medium_severe_rate_pct']} |
| medium_risk_penalty_v5 | -{summary['medium_risk_penalty_v5']} |
| hard_severe_rate_pct | {summary['hard_severe_rate_pct']} |
| hard_risk_penalty_v5 | -{summary['hard_risk_penalty_v5']} |
| difficulty_risk_penalty_v5 | -{summary['difficulty_risk_penalty_v5']} |
| reliability_penalty_v5 | {summary['reliability_penalty_v5']} |
| direct_usable_rate_pct | {summary['direct_usable_rate_pct']} |
| completion_rate_pct | {summary['completion_rate_pct']} |
| safety_score_pct | {summary['safety_score_pct']} |
| severe_rate_pct | {summary['severe_rate_pct']} |
| avg_ned | {summary['avg_ned']} |
| global_sample_mean_score_v5 | {summary['global_sample_mean_score_v5']}（仅诊断） |

## 分类诊断

| 主类别 | 总数 | 已评分 | 分数 | severe |
| --- | ---: | ---: | ---: | ---: |
{category_rows}

## 难度诊断

| 难度 | 总数 | 已评分 | 分数 | severe |
| --- | ---: | ---: | ---: | ---: |
{difficulty_rows}

## 主要错误标签

| 标签 | 数量 |
| --- | ---: |
{tags}

## 结论

- 最弱主类别：{summary['weakest_category']} {summary['weakest_category_name']}。
- 最弱难度：{summary['weakest_difficulty']}。
- 当前 304 题已冻结，冻结 ID 为 `{summary['dataset_version']}`。
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build OCR Benchmark v5 scores from predictions and LLM judge output.")
    parser.add_argument("--manifest", type=Path, default=Path("testset/manifest.jsonl"))
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--judge", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--samples-output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--prompt-group", default="short_prompt")
    parser.add_argument("--dataset-version", default="code_ocr_eval_benchmark_v5_content_5_2_photo30_20260710")
    parser.add_argument("--content-version", default="5.2")
    parser.add_argument("--dataset-revision")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_rows, manifest_by_image = load_manifest(args.manifest)
    predictions = read_jsonl(args.predictions)
    judgements = read_jsonl(args.judge)
    rows = build_rows(manifest_rows, manifest_by_image, predictions, judgements)
    summary = aggregate(
        rows,
        len(manifest_rows),
        args.run_name,
        args.prompt_group,
        args.predictions,
        args.judge,
        args.dataset_version,
        args.content_version,
        args.dataset_revision,
    )
    write_json(args.summary, summary)
    write_jsonl(args.samples_output, rows)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown_report(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
