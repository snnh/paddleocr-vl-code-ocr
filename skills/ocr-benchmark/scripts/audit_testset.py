from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_number}: JSON 无效: {exc}") from exc
    return rows


def resolve_inside(root: Path, reference: str) -> Path | None:
    path = (root / reference).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="审计 OCR 测试集 manifest 和文件完整性。")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, help="默认使用 <root>/manifest.jsonl。")
    parser.add_argument("--train-images", type=Path, help="可选训练图片目录，用于 SHA-256 防泄漏检查。")
    parser.add_argument("--output", type=Path, help="可选 JSON 汇总输出。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    manifest = (args.manifest or root / "manifest.jsonl").resolve()
    rows = load_jsonl(manifest)
    findings: list[dict] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    seen_hashes: set[str] = set()
    test_hashes: set[str] = set()
    for index, row in enumerate(rows, start=1):
        sample_id = str(row.get("id") or "")
        image_ref = row.get("image") or ((row.get("images") or [None])[0])
        annotation_ref = row.get("annotation")
        if not sample_id:
            findings.append({"row": index, "type": "missing_id"})
        elif sample_id in seen_ids:
            findings.append({"id": sample_id, "type": "duplicate_id"})
        seen_ids.add(sample_id)
        if not image_ref:
            findings.append({"id": sample_id, "type": "missing_image_path"})
            continue
        image_ref = str(image_ref).replace("\\", "/").removeprefix("./")
        if image_ref in seen_paths:
            findings.append({"id": sample_id, "type": "duplicate_image_path", "path": image_ref})
        seen_paths.add(image_ref)
        image_path = resolve_inside(root, image_ref)
        if image_path is None:
            findings.append({"id": sample_id, "type": "image_path_outside_root", "path": image_ref})
            continue
        if not image_path.is_file():
            findings.append({"id": sample_id, "type": "missing_image_file", "path": image_ref})
        else:
            actual_hash = sha256(image_path)
            test_hashes.add(actual_hash)
            if actual_hash in seen_hashes:
                findings.append({"id": sample_id, "type": "duplicate_image_hash", "sha256": actual_hash})
            seen_hashes.add(actual_hash)
            declared_hash = row.get("image_sha256") or row.get("sha256")
            if declared_hash and str(declared_hash).lower() != actual_hash:
                findings.append({"id": sample_id, "type": "image_hash_mismatch"})
        if annotation_ref:
            annotation_ref = str(annotation_ref).replace("\\", "/").removeprefix("./")
            annotation_path = resolve_inside(root, annotation_ref)
            if annotation_path is None:
                findings.append(
                    {"id": sample_id, "type": "annotation_path_outside_root", "path": annotation_ref}
                )
                continue
            if not annotation_path.is_file():
                findings.append({"id": sample_id, "type": "missing_annotation_file", "path": annotation_ref})
            else:
                annotation_text = annotation_path.read_text(encoding="utf-8")
                if not annotation_text.strip():
                    findings.append({"id": sample_id, "type": "empty_annotation"})
                declared_annotation_hash = row.get("annotation_sha256")
                if declared_annotation_hash and str(declared_annotation_hash).lower() != sha256(annotation_path):
                    findings.append({"id": sample_id, "type": "annotation_hash_mismatch"})
        elif not str(row.get("label") or row.get("text") or row.get("ground_truth") or "").strip():
            findings.append({"id": sample_id, "type": "missing_annotation_or_label"})
    overlap = 0
    if args.train_images:
        train_hashes = {
            sha256(path)
            for path in args.train_images.resolve().rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        }
        overlap = len(test_hashes & train_hashes)
        if overlap:
            findings.append({"type": "train_test_image_hash_overlap", "count": overlap})
    summary = {
        "root": str(root),
        "manifest": str(manifest),
        "records": len(rows),
        "unique_ids": len(seen_ids),
        "unique_image_paths": len(seen_paths),
        "unique_image_hashes": len(seen_hashes),
        "train_test_image_hash_overlap": overlap,
        "blocking_findings": len(findings),
        "findings": findings,
    }
    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    raise SystemExit(1 if findings else 0)


if __name__ == "__main__":
    main()
