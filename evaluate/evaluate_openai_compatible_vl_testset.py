import argparse
import ast
import base64
import concurrent.futures as futures
import io
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
import threading
import time

import requests


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DEV_OCR_PROMPT = """请对这张图片执行开发场景 OCR，只输出转写文本。

要求：
- 转写图片中主要可读的开发相关文本，不限于纯代码。
- 主要目标包括代码、配置、命令、终端输出、Notebook、调试器、数据库/REST/API 工具、错误/诊断列表、补全框、命令面板、文件名/标签页、开发说明文本等。
- 尽量保留原始换行、缩进、大小写、标点、括号、引号、运算符、路径、文件名和空格。
- 不要解释，不要评价，不要输出 Markdown 代码围栏。
- 不要补全图片中看不见的内容。
- 如果画面有多个主要文本区域，用空行或 --- 分隔，保持自然阅读顺序。"""
OVISOCR2_PROMPT = """
Extract all readable content from the image in natural human reading order and output the result as a single Markdown document. For charts or images, represent them using an HTML image tag: <img src="images/bbox_{left}_{top}_{right}_{bottom}.jpg" />, where left, top, right, bottom are bounding box coordinates scaled to [0, 1000). Format formulas as LaTeX. Format tables as HTML: <table>...</table>. Transcribe all other text as standard Markdown. Preserve the original text without translation or paraphrasing."""


WRITE_LOCK = threading.Lock()


def read_token_from_file(path: Path, variable_name: str):
    if not path or not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(variable_name) and "=" in line:
            _, value = line.split("=", 1)
            value = value.strip()
            try:
                parsed = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                parsed = value.strip("\"'")
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


def load_samples(path):
    samples = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            sample = json.loads(line)
            samples.append(
                {
                    "index": line_number,
                    "image": sample["images"][0],
                    "prompt": sample["messages"][0]["content"],
                    "label": sample["messages"][1]["content"],
                }
            )
    return samples


def load_done(path):
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


def resolve_image_path(image_ref, data_path):
    raw = image_ref[2:] if image_ref.startswith("./") else image_ref
    candidates = [Path.cwd() / raw, data_path.parent / raw]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"image not found for {image_ref}")


def image_data_url(path: Path, max_image_pixels=None):
    should_resize = False
    original_size = None
    if max_image_pixels:
        from PIL import Image

        with Image.open(path) as image:
            original_size = image.size
            should_resize = image.width * image.height > max_image_pixels
    if path.suffix.lower() == ".webp" or should_resize:
        try:
            from PIL import Image

            with Image.open(path) as image:
                if should_resize:
                    scale = (max_image_pixels / (image.width * image.height)) ** 0.5
                    resized_size = (
                        max(1, int(image.width * scale)),
                        max(1, int(image.height * scale)),
                    )
                    image = image.resize(resized_size, Image.Resampling.LANCZOS)
                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGB")
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
            payload = base64.b64encode(buffer.getvalue()).decode("ascii")
            preprocessing = None
            if should_resize:
                preprocessing = {
                    "method": "resize_max_pixels_lanczos_png",
                    "max_image_pixels": max_image_pixels,
                    "original_size": list(original_size),
                    "request_size": list(resized_size),
                }
            return f"data:image/png;base64,{payload}", preprocessing
        except Exception as exc:
            print(f"warning: failed to convert WebP to PNG for {path}: {exc}", file=sys.stderr)
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{payload}", None


def clean_prediction(text):
    text = text.strip()
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1].strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:text|txt|[a-zA-Z0-9_+-]+)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def clean_truncated_repeats(
    text,
    min_text_len=8000,
    max_period=200,
    min_period=1,
    min_repeat_chars=100,
    min_repeat_times=5,
):
    """Match the repeat-tail cleanup used by the official OvisOCR2 parser."""
    n = len(text)
    if n < min_text_len:
        return text
    max_period = min(max_period, n - 1)
    for unit_len in range(min_period, max_period + 1):
        if text[n - 1] != text[n - 1 - unit_len]:
            continue
        match_len = 1
        idx = n - 2
        while idx >= unit_len and text[idx] == text[idx - unit_len]:
            match_len += 1
            idx -= 1
        total_len = match_len + unit_len
        repeat_times = total_len // unit_len
        tail_len = total_len % unit_len
        if repeat_times >= min_repeat_times and total_len >= min_repeat_chars:
            return text[: n - total_len + unit_len] + text[n - tail_len :]
    return text


def postprocess_prediction(text, profile):
    text = clean_prediction(text)
    if profile == "ovisocr2":
        text = "\n\n".join(
            block
            for block in text.split("\n\n")
            if not block.strip().startswith('<img src="images/bbox_')
        )
        text = clean_truncated_repeats(text)
    return text.strip()


def extract_response_text(data):
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        pass
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    raise RuntimeError(f"could not extract response text: {json.dumps(data, ensure_ascii=False)[:800]}")


def call_model(image_path, prompt, api_key, args):
    image_url, image_preprocessing = image_data_url(image_path, args.max_image_pixels)
    content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": image_url, "detail": args.detail}},
    ]
    if args.image_first:
        content.reverse()
    payload = {
        "model": args.model,
        "messages": [
            {
                "role": "user",
                "content": content,
            }
        ],
    }
    if args.mm_min_pixels is not None or args.mm_max_pixels is not None:
        images_kwargs = {}
        if args.mm_min_pixels is not None:
            images_kwargs["min_pixels"] = args.mm_min_pixels
        if args.mm_max_pixels is not None:
            images_kwargs["max_pixels"] = args.mm_max_pixels
        payload["mm_processor_kwargs"] = {"images_kwargs": images_kwargs}
    if not args.omit_temperature:
        payload["temperature"] = args.temperature
    if args.disable_web_search:
        payload["web_search"] = {"enable": False}
    if args.reasoning_effort:
        payload["reasoning_effort"] = args.reasoning_effort
    if args.max_completion_tokens:
        payload["max_completion_tokens"] = args.max_completion_tokens
    elif args.max_tokens and args.max_tokens > 0:
        payload["max_tokens"] = args.max_tokens
    if args.repetition_penalty is not None:
        payload["repetition_penalty"] = args.repetition_penalty
    if args.presence_penalty is not None:
        payload["presence_penalty"] = args.presence_penalty
    if args.frequency_penalty is not None:
        payload["frequency_penalty"] = args.frequency_penalty
    if args.top_p is not None:
        payload["top_p"] = args.top_p
    if args.top_k is not None:
        payload["top_k"] = args.top_k
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": args.user_agent,
    }
    response = None
    last_error = None
    for attempt in range(args.retries + 1):
        try:
            response = requests.post(args.url, headers=headers, json=payload, timeout=args.timeout)
            is_rate_limited = response.status_code == 429 or (
                response.status_code == 403 and "访问过于频繁" in response.text
            )
            if not is_rate_limited:
                break
            last_error = RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")
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
    raw_prediction = extract_response_text(data).strip()
    prediction = postprocess_prediction(raw_prediction, args.prediction_postprocess)
    return prediction, raw_prediction, data, image_preprocessing


def levenshtein_distance(a, b):
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (0 if ca == cb else 1))
            )
        previous = current
    return previous[-1]


def normalized_edit_distance(prediction, label):
    prediction = prediction.replace("\r\n", "\n").replace("\r", "\n").strip()
    label = label.replace("\r\n", "\n").replace("\r", "\n").strip()
    max_len = max(len(prediction), len(label))
    if max_len == 0:
        return 0.0
    return levenshtein_distance(prediction, label) / max_len


def write_jsonl(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with WRITE_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            handle.flush()


def write_summary(path, records, model, args):
    neds = [record["ned"] for record in records]
    exact = [record for record in records if record["prediction"].strip() == record["label"].strip()]
    trimmed = sorted(neds)[1:-1] if len(neds) > 2 else neds
    reasoning_efforts = sorted({record.get("reasoning_effort") for record in records if record.get("reasoning_effort")})
    summary = {
        "model": model,
        "reasoning_effort": reasoning_efforts[0] if len(reasoning_efforts) == 1 else reasoning_efforts or None,
        "request_parameters": {
            "temperature": None if args.omit_temperature else args.temperature,
            "top_p": args.top_p,
            "top_k": args.top_k,
            "repetition_penalty": args.repetition_penalty,
            "max_tokens": args.max_tokens if args.max_tokens and args.max_tokens > 0 else None,
            "max_completion_tokens": args.max_completion_tokens,
            "image_first": args.image_first,
            "mm_min_pixels": args.mm_min_pixels,
            "mm_max_pixels": args.mm_max_pixels,
            "prediction_postprocess": args.prediction_postprocess,
            "eval_prompt_profile": args.eval_prompt_profile,
        },
        "preprocessed_records": sum(1 for record in records if record.get("image_preprocessing")),
        "samples": len(records),
        "avg_ned": sum(neds) / len(neds) if neds else None,
        "trimmed_avg_ned": sum(trimmed) / len(trimmed) if trimmed else None,
        "exact_match": len(exact),
        "exact_match_rate": len(exact) / len(records) if records else None,
        "best_ned": min(neds) if neds else None,
        "worst_ned": max(neds) if neds else None,
    }
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def evaluate_sample(sample, api_key, args, total):
    image_path = resolve_image_path(sample["image"], args.data_path)
    prompt = sample["prompt"] if args.use_sample_prompt else args.eval_prompt
    prediction, raw_prediction, response_data, image_preprocessing = call_model(image_path, prompt, api_key, args)
    ned = normalized_edit_distance(prediction, sample["label"])
    return {
        "image": sample["image"],
        "prompt": sample["prompt"],
        "request_prompt": prompt,
        "label": sample["label"],
        "prediction": prediction,
        "raw_prediction": raw_prediction if raw_prediction != prediction else None,
        "prediction_postprocessing": args.prediction_postprocess,
        "ned": ned,
        "edit_distance": levenshtein_distance(prediction.strip(), sample["label"].strip()),
        "label_chars": len(sample["label"]),
        "prediction_chars": len(prediction),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "usage": response_data.get("usage"),
        "image_preprocessing": image_preprocessing,
        "index": sample["index"],
        "total": total,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate an OpenAI-compatible VLM OCR model on a JSONL test set.")
    parser.add_argument("--data-path", type=Path, default=Path("test.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--errors", type=Path, required=True)
    parser.add_argument("--api-key")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--user-agent", default="OpenAI/Python 1.0")
    parser.add_argument("--detail", choices=["low", "high", "auto"], default="high")
    parser.add_argument(
        "--max-image-pixels",
        type=int,
        help="Resize larger images in memory to this pixel area before submitting; original files are unchanged.",
    )
    parser.add_argument("--image-first", action="store_true", help="Place the image before text in chat content.")
    parser.add_argument("--mm-min-pixels", type=int, help="Pass images_kwargs.min_pixels to the model processor.")
    parser.add_argument("--mm-max-pixels", type=int, help="Pass images_kwargs.max_pixels to the model processor.")
    parser.add_argument(
        "--prediction-postprocess",
        choices=["none", "ovisocr2"],
        default="none",
        help="Apply a documented model-specific output cleanup while retaining changed raw text.",
    )
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--retry-sleep-seconds", type=float, default=20.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=4096, help="Use 0 to omit max_tokens from the request.")
    parser.add_argument("--max-completion-tokens", type=int)
    parser.add_argument("--repetition-penalty", type=float)
    parser.add_argument("--presence-penalty", type=float)
    parser.add_argument("--frequency-penalty", type=float)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--omit-temperature", action="store_true")
    parser.add_argument("--disable-web-search", action="store_true")
    parser.add_argument("--reasoning-effort", choices=["minimal", "low", "medium", "high"])
    parser.add_argument("--only-index", type=int, help="Evaluate only the 1-based sample index in the data file.")
    parser.add_argument("--start-index", type=int, help="Evaluate samples with 1-based index >= this value.")
    parser.add_argument("--end-index", type=int, help="Evaluate samples with 1-based index <= this value.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--eval-prompt")
    parser.add_argument(
        "--eval-prompt-profile",
        choices=["dev_ocr", "ovisocr2"],
        default="dev_ocr",
        help="Use a built-in prompt unless --eval-prompt is provided.",
    )
    parser.add_argument("--use-sample-prompt", action="store_true")
    return parser.parse_args()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    if args.eval_prompt is None:
        args.eval_prompt = OVISOCR2_PROMPT if args.eval_prompt_profile == "ovisocr2" else DEV_OCR_PROMPT
    if args.workers < 1:
        raise SystemExit("--workers must be >= 1")
    if args.mm_min_pixels is not None and args.mm_min_pixels < 1:
        raise SystemExit("--mm-min-pixels must be >= 1")
    if args.mm_max_pixels is not None and args.mm_max_pixels < 1:
        raise SystemExit("--mm-max-pixels must be >= 1")
    if (
        args.mm_min_pixels is not None
        and args.mm_max_pixels is not None
        and args.mm_min_pixels > args.mm_max_pixels
    ):
        raise SystemExit("--mm-min-pixels must be <= --mm-max-pixels")
    api_key = load_api_key(args)
    samples = load_samples(args.data_path)
    if args.only_index is not None:
        samples = [sample for sample in samples if sample["index"] == args.only_index]
    if args.start_index is not None:
        samples = [sample for sample in samples if sample["index"] >= args.start_index]
    if args.end_index is not None:
        samples = [sample for sample in samples if sample["index"] <= args.end_index]
    if args.limit is not None:
        samples = samples[: args.limit]
    done = load_done(args.output)
    pending = [sample for sample in samples if sample["image"] not in done]
    print(f"samples={len(samples)} done={len(done)} pending={len(pending)} workers={args.workers} model={args.model}")
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_to_sample = {pool.submit(evaluate_sample, sample, api_key, args, len(samples)): sample for sample in pending}
        for index, future in enumerate(futures.as_completed(future_to_sample), start=1):
            sample = future_to_sample[future]
            try:
                record = future.result()
                write_jsonl(args.output, record)
                done[sample["image"]] = record
                print(
                    f"[{index}/{len(pending)}] done {sample['image']} "
                    f"ned={record['ned']:.4f} pred_chars={record['prediction_chars']} "
                    f"label_chars={record['label_chars']}",
                    flush=True,
                )
            except Exception as exc:
                write_jsonl(args.errors, {"image": sample["image"], "error": str(exc), "model": args.model})
                print(f"[{index}/{len(pending)}] error {sample['image']}: {exc}", file=sys.stderr, flush=True)
    records = list(load_done(args.output).values())
    records.sort(key=lambda item: item["image"])
    print(json.dumps(write_summary(args.summary, records, args.model, args), ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
