from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="规划或创建 OCR 测试集目录骨架。")
    parser.add_argument("--root", type=Path, required=True, help="测试集根目录。")
    parser.add_argument("--layout", choices=["minimal", "extended"], default="extended")
    parser.add_argument("--categories", nargs="*", default=[], help="可选类别目录名。")
    parser.add_argument("--difficulties", nargs="*", default=[], help="可选难度目录名。")
    parser.add_argument("--apply", action="store_true", help="实际创建；默认仅显示计划。")
    return parser.parse_args()


def data_dirs(root: Path, base: str, difficulties: list[str], categories: list[str]) -> list[Path]:
    if difficulties and categories:
        return [root / base / difficulty / category for difficulty in difficulties for category in categories]
    if difficulties:
        return [root / base / difficulty for difficulty in difficulties]
    if categories:
        return [root / base / category for category in categories]
    return [root / base]


def validate_segments(values: list[str], label: str) -> None:
    for value in values:
        if not value or value in {".", ".."} or "/" in value or "\\" in value:
            raise SystemExit(f"{label} 包含不安全目录名: {value!r}")


def main() -> None:
    args = parse_args()
    validate_segments(args.categories, "--categories")
    validate_segments(args.difficulties, "--difficulties")
    root = args.root.resolve()
    directories = data_dirs(root, "images", args.difficulties, args.categories)
    directories += data_dirs(root, "annotations", args.difficulties, args.categories)
    files: dict[Path, str] = {
        root / "manifest.jsonl": "",
        root / "test.jsonl": "",
    }
    if args.layout == "extended":
        directories.append(root / "audit")
        files.update(
            {
                root / "test.json": "[]\n",
                root / "tags.tsv": "id\ttext_density\tlegibility\tcapture_type\trisk_tags\n",
                root / "FREEZE.md": "# 测试集冻结记录\n\n状态：待冻结\n",
                root / "data_statement.md": "# 测试集数据声明\n\n请填写来源、标注、审核、防泄漏和许可信息。\n",
            }
        )
    plan = {
        "root": str(root),
        "layout": args.layout,
        "directories": [str(path.relative_to(root)) for path in sorted(set(directories))],
        "files": [str(path.relative_to(root)) for path in sorted(files)],
        "apply": args.apply,
    }
    if not args.apply:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    created = []
    skipped = []
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            skipped.append(str(path.relative_to(root)))
            continue
        path.write_text(content, encoding="utf-8", newline="\n")
        created.append(str(path.relative_to(root)))
    plan["created_files"] = created
    plan["skipped_existing_files"] = skipped
    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
