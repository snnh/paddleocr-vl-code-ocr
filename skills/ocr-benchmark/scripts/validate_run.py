from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def load_records(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        value = json.loads(text)
        if not isinstance(value, list):
            raise SystemExit(f"{path}: 顶层 JSON 必须是数组")
        return value
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def record_key(row: dict, prefixes: list[str]) -> str:
    value = row.get("image") or row.get("id")
    if not value and row.get("images"):
        value = row["images"][0]
    key = str(value or "").replace("\\", "/").removeprefix("./")
    for prefix in prefixes:
        normalized = prefix.replace("\\", "/").removeprefix("./").rstrip("/") + "/"
        if key.startswith(normalized):
            key = key[len(normalized) :]
    return key


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="核验测试入口、预测和裁判记录完整性。")
    parser.add_argument("--test-data", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--judge", type=Path)
    parser.add_argument("--expected-records", type=int)
    parser.add_argument("--strip-prefix", action="append", default=[])
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def duplicate_keys(keys: list[str]) -> list[str]:
    return sorted(key for key, count in Counter(keys).items() if key and count > 1)


def main() -> None:
    args = parse_args()
    test_rows = load_records(args.test_data)
    prediction_rows = load_records(args.predictions)
    judge_rows = load_records(args.judge) if args.judge else []
    test_keys = [record_key(row, args.strip_prefix) for row in test_rows]
    prediction_keys = [record_key(row, args.strip_prefix) for row in prediction_rows]
    judge_keys = [record_key(row, args.strip_prefix) for row in judge_rows]
    test_set = {key for key in test_keys if key}
    prediction_set = {key for key in prediction_keys if key}
    judge_set = {key for key in judge_keys if key}
    expected = args.expected_records if args.expected_records is not None else len(test_rows)
    summary = {
        "expected_records": expected,
        "test_records": len(test_rows),
        "test_unique_keys": len(test_set),
        "prediction_records": len(prediction_rows),
        "prediction_unique_keys": len(prediction_set),
        "prediction_duplicates": duplicate_keys(prediction_keys),
        "prediction_missing": sorted(test_set - prediction_set),
        "prediction_extra": sorted(prediction_set - test_set),
        "empty_predictions": sorted(
            record_key(row, args.strip_prefix)
            for row in prediction_rows
            if not str(row.get("prediction") or "").strip()
        ),
        "judge_records": len(judge_rows) if args.judge else None,
        "judge_unique_keys": len(judge_set) if args.judge else None,
        "judge_duplicates": duplicate_keys(judge_keys) if args.judge else [],
        "judge_missing": sorted(prediction_set - judge_set) if args.judge else [],
        "judge_extra": sorted(judge_set - prediction_set) if args.judge else [],
    }
    blocking = bool(
        len(test_rows) != expected
        or summary["prediction_duplicates"]
        or summary["prediction_extra"]
        or summary["empty_predictions"]
        or summary["judge_duplicates"]
        or summary["judge_extra"]
        or (not args.allow_missing and (summary["prediction_missing"] or summary["judge_missing"]))
    )
    summary["blocking"] = blocking
    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    raise SystemExit(1 if blocking else 0)


if __name__ == "__main__":
    main()
