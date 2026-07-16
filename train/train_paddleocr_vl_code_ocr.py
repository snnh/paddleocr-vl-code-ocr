"""Validate data, generate the v6 PaddleFormers config, and optionally train.

The default mode is a dry run. It validates message-format JSON/JSONL files,
checks image SHA-256 overlap between splits, and writes the exact public v6
LoRA configuration. Pass ``--run`` only after reviewing the generated YAML.

The final evaluation split is never passed to the trainer. It is accepted only
so the preflight check can reject train/evaluation leakage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "PaddlePaddle/PaddleOCR-VL-1.6"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs" / "paddleocr_vl_code_ocr_v6_lora"
DEFAULT_CONFIG = REPO_ROOT / "outputs" / "training_config" / "paddleocr_vl_code_ocr_v6_lora.yaml"
PROMPT = "<image>OCR:"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and optionally run the public PaddleOCR-VL-1.6 v6 LoRA recipe."
    )
    parser.add_argument("--train-data", type=Path, required=True, help="Message-format JSON or JSONL.")
    parser.add_argument("--dev-data", type=Path, help="Optional validation JSON or JSONL.")
    parser.add_argument(
        "--final-eval-data",
        type=Path,
        help="Optional final benchmark split; checked for leakage but never used by training.",
    )
    parser.add_argument("--config-out", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model-name-or-path", default=DEFAULT_MODEL)
    parser.add_argument("--cuda-visible-devices", default="0")
    parser.add_argument("--paddleformers-cli", default="paddleformers-cli")
    parser.add_argument("--run", action="store_true", help="Launch training after preflight checks.")
    return parser.parse_args()


def read_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset does not exist: {path}")

    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"{path}: top-level JSON value must be an array")
        records = payload
    else:
        records = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: invalid JSONL: {exc}") from exc

    if not records:
        raise ValueError(f"{path}: no records")
    if not all(isinstance(record, dict) for record in records):
        raise ValueError(f"{path}: every record must be a JSON object")
    return records


def resolve_image(path: Path, image_ref: str) -> Path:
    image_path = Path(image_ref)
    if image_path.is_absolute():
        return image_path.resolve()

    candidates = [
        (path.parent / image_path).resolve(),
        (Path.cwd() / image_path).resolve(),
        (REPO_ROOT / image_path).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_split(path: Path) -> tuple[int, set[str]]:
    records = read_records(path)
    image_hashes: set[str] = set()

    for index, record in enumerate(records, start=1):
        messages = record.get("messages")
        images = record.get("images")
        if not isinstance(messages, list) or len(messages) != 2:
            raise ValueError(f"{path}:{index}: expected exactly two messages")
        if messages[0].get("role") != "user" or messages[1].get("role") != "assistant":
            raise ValueError(f"{path}:{index}: expected user then assistant roles")
        if messages[0].get("content") != PROMPT:
            raise ValueError(f"{path}:{index}: prompt must be {PROMPT!r}")
        answer = messages[1].get("content")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(f"{path}:{index}: empty OCR target")
        if not isinstance(images, list) or len(images) != 1 or not isinstance(images[0], str):
            raise ValueError(f"{path}:{index}: expected one image path")

        image_path = resolve_image(path, images[0])
        if not image_path.exists():
            raise FileNotFoundError(f"{path}:{index}: missing image: {images[0]}")
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError(f"{path}:{index}: unsupported image type: {image_path.suffix}")
        image_hash = sha256_file(image_path)
        if image_hash in image_hashes:
            raise ValueError(f"{path}:{index}: duplicate image SHA-256 within split")
        image_hashes.add(image_hash)

    return len(records), image_hashes


def validate_no_overlap(splits: dict[str, set[str]]) -> None:
    names = list(splits)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            overlap = splits[left] & splits[right]
            if overlap:
                preview = ", ".join(sorted(overlap)[:5])
                raise ValueError(f"Image SHA-256 overlap between {left} and {right}: {preview}")


def yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value).replace("\\", "/"), ensure_ascii=False)


def build_config(args: argparse.Namespace) -> dict[str, Any]:
    config: dict[str, Any] = {
        "train_dataset_type": "messages",
        "train_dataset_path": str(args.train_data.resolve()),
        "train_dataset_prob": "1.0",
        "max_seq_len": 16384,
        "padding_free": True,
        "truncate_packing": False,
        "dataloader_num_workers": 4,
        "mix_strategy": "concat",
        "template_backend": "custom",
        "template": "paddleocr_vl",
        "model_name_or_path": args.model_name_or_path,
        "_attn_implementation": "flashmask",
        "stage": "VL-SFT",
        "fine_tuning": "lora",
        "lora": True,
        "lora_rank": 8,
        "seed": 23,
        "do_train": True,
        "do_eval": args.dev_data is not None,
        "per_device_train_batch_size": 1,
        "per_device_eval_batch_size": 1,
        "gradient_accumulation_steps": 2,
        "num_train_epochs": 2,
        "max_steps": -1,
        "evaluation_strategy": "steps" if args.dev_data else "no",
        "eval_steps": 50,
        "save_strategy": "steps",
        "save_steps": 50,
        "logging_steps": 1,
        "logging_dir": str((args.output_dir / "visualdl_logs").resolve()),
        "output_dir": str(args.output_dir.resolve()),
        "disable_tqdm": True,
        "lr_scheduler_type": "cosine",
        "learning_rate": 2.0e-4,
        "min_lr": 2.0e-5,
        "warmup_ratio": 0.1,
        "weight_decay": 0.01,
        "adam_epsilon": 1.0e-8,
        "adam_beta1": 0.9,
        "adam_beta2": 0.95,
        "tensor_model_parallel_size": 1,
        "pipeline_model_parallel_size": 1,
        "sharding": "stage2",
        "recompute_granularity": "full",
        "recompute_method": "uniform",
        "recompute_num_layers": 1,
        "bf16": True,
        "fp16_opt_level": "O2",
        "unified_checkpoint": False,
        "save_checkpoint_format": "flex_checkpoint",
        "load_checkpoint_format": "flex_checkpoint",
    }
    if args.dev_data:
        config.update(
            {
                "eval_dataset_type": "messages",
                "eval_dataset_path": str(args.dev_data.resolve()),
                "eval_dataset_prob": "1.0",
            }
        )
    return config


def write_config(path: Path, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# PaddleOCR-VL-1.6 developer-code OCR v6 public reproduction config",
        "# Generated by train/train_paddleocr_vl_code_ocr.py",
    ]
    for key, value in config.items():
        lines.append(f"{key}: {yaml_scalar(value)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def train_command(args: argparse.Namespace) -> list[str]:
    return [
        args.paddleformers_cli,
        "train",
        str(args.config_out.resolve()),
        f"pre_alloc_memory=16",
    ]


def main() -> int:
    args = parse_args()
    splits: dict[str, set[str]] = {}
    counts: dict[str, int] = {}
    for name, path in (
        ("train", args.train_data),
        ("dev", args.dev_data),
        ("final_eval", args.final_eval_data),
    ):
        if path is None:
            continue
        count, hashes = validate_split(path)
        counts[name] = count
        splits[name] = hashes
    validate_no_overlap(splits)

    config = build_config(args)
    write_config(args.config_out, config)
    command = train_command(args)

    print(json.dumps({
        "model": args.model_name_or_path,
        "records": counts,
        "sha256_overlap": 0,
        "config": str(args.config_out.resolve()),
        "output_dir": str(args.output_dir.resolve()),
        "command": command,
        "final_eval_used_for_training": False,
    }, ensure_ascii=False, indent=2))

    if not args.run:
        print("dry_run=true; review the generated YAML, then rerun with --run")
        return 0
    if shutil.which(args.paddleformers_cli) is None:
        raise FileNotFoundError(f"Cannot find executable: {args.paddleformers_cli}")

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = args.cuda_visible_devices
    completed = subprocess.run(command, cwd=REPO_ROOT, env=env, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
