import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
BAD_PATTERNS = [
    "无法识别图像",
    "无法准确识别",
    "无法判断图中",
    "图像不清晰",
    "看不清图中",
    "抱歉，我无法",
    "sorry, i cannot",
    "sorry, i can't",
    "as an ai",
    "<image>",
]


def collect_images(folder: Path):
    return {
        path.stem: path
        for path in sorted(folder.iterdir(), key=lambda item: item.name)
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    }


def audit_folder(folder: Path):
    images = collect_images(folder)
    text_files = {
        path.stem: path
        for path in sorted(folder.iterdir(), key=lambda item: item.name)
        if path.is_file() and path.suffix.lower() == ".txt"
    }
    findings = []

    for stem, image_path in images.items():
        text_path = text_files.get(stem)
        if not text_path:
            findings.append((stem, "missing_txt", image_path.name))
            continue
        text = text_path.read_text(encoding="utf-8", errors="replace")
        normalized = text.strip().lower()
        if not normalized:
            findings.append((stem, "empty_txt", text_path.name))
            continue
        for pattern in BAD_PATTERNS:
            if pattern in normalized:
                findings.append((stem, f"bad_pattern:{pattern}", text_path.name))
                break

    for stem, text_path in text_files.items():
        if stem not in images:
            findings.append((stem, "missing_image", text_path.name))

    return findings


def main():
    parser = argparse.ArgumentParser(description="Audit flat OCR image/txt folders for hard quality failures.")
    parser.add_argument("folders", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "annotations" / "quality_audit_findings.tsv")
    args = parser.parse_args()

    rows = []
    for folder in args.folders:
        folder = folder if folder.is_absolute() else ROOT / folder
        for stem, reason, file_name in audit_folder(folder):
            rows.append((folder.relative_to(ROOT).as_posix(), stem, reason, file_name))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("folder\tstem\treason\tfile\n")
        for row in rows:
            handle.write("\t".join(row) + "\n")

    print(f"findings={len(rows)}")
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
