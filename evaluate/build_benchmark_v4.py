import argparse
import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "evaluations" / "benchmark_v4"
DEFAULT_MANIFEST = ROOT / "benchmark_v4_workspace" / "final_ui" / "by_category_manifest.jsonl"
TOTAL_SAMPLES = 100
DIMENSION_POWER = 1.4
CATEGORY_WEIGHTS = {
    "IDE 代码编辑器截图": 0.15,
    "终端 / Shell / PowerShell": 0.07,
    "报错日志 / Traceback": 0.17,
    "配置文件 / YAML / JSON / TOML / INI": 0.14,
    "Git diff / patch / PR 页面": 0.07,
    "网页代码块 / 文档代码块": 0.10,
    "表格化代码信息 / 参数表 / API 文档": 0.12,
    "模糊、压缩、拍屏、暗色主题、小字号等困难样本": 0.18,
}

DIM_FIELDS = [
    ("content_coverage_0_10", 10, 0.24),
    ("symbol_accuracy_0_10", 10, 0.30),
    ("indentation_alignment_0_10", 10, 0.18),
    ("structure_format_0_10", 10, 0.12),
    ("reading_region_order_0_10", 10, 0.16),
]
SCORE_DIM_FIELDS = [
    ("content_coverage_0_10", 10, 0.20),
    ("symbol_accuracy_0_10", 10, 0.24),
    ("indentation_alignment_0_10", 10, 0.16),
    ("structure_format_0_10", 10, 0.14),
    ("reading_region_order_0_10", 10, 0.10),
    ("noise_and_usability_0_10", 10, 0.16),
]
NOISE_FIELD = "noise_and_usability_0_10"
LEGACY_DIM_FIELDS = {
    "content_coverage_0_10": ("content_coverage_0_30", 30),
    "symbol_accuracy_0_10": ("symbol_accuracy_0_25", 25),
    "structure_format_0_10": ("structure_format_0_5", 5),
    "noise_and_usability_0_10": ("noise_and_usability_0_20", 20),
}


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_manifest(path: Path) -> tuple[dict[str, str], dict[str, int]]:
    file_to_category = {}
    counts = {}
    for row in load_jsonl(path):
        file_to_category[row["file"]] = row["category"]
        counts[row["category"]] = counts.get(row["category"], 0) + 1
    return file_to_category, counts


def image_file_name(record: dict) -> str:
    image = str(record.get("image") or "")
    normalized = image.replace("\\", "/")
    return normalized.rsplit("/", 1)[-1]


def trimmed_mean(values: list[float]) -> float | None:
    if not values:
        return None
    if len(values) <= 2:
        return sum(values) / len(values)
    ordered = sorted(values)
    trimmed = ordered[1:-1]
    return sum(trimmed) / len(trimmed)


def infer_prompt_policy(name: str) -> str:
    lowered = name.lower()
    if "strictprompt" in lowered:
        return "strict_ocr_prompt"
    if "sampleprompt" in lowered:
        return "<image>OCR:"
    if "devocr" in lowered:
        return "dev_ocr_prompt"
    if "layout" in lowered:
        return "layout_api"
    if "api" in lowered:
        return "api_default"
    if "ppocr" in lowered or "paddleocr" in lowered:
        return "<image>OCR:"
    return "unspecified"


def prompt_group(prompt_policy: str) -> str:
    if prompt_policy == "<image>OCR:":
        return "short_prompt"
    if prompt_policy in {"strict_ocr_prompt", "dev_ocr_prompt"}:
        return "long_or_strict_prompt"
    return "other_prompt"


def infer_run_name(path: Path) -> str:
    name = path.stem
    prefix = "llm_judge_"
    if name.startswith(prefix):
        name = name[len(prefix) :]
    for suffix in ("_deepseek_v4_flash_v4", "_deepseek_v4_flash_v3", "_dev_ocr_judge_v4", "_dev_ocr_judge_v3"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name


def dim_ratio(dims: dict, key: str, max_score: int) -> float:
    if key in dims:
        value = float(dims.get(key, 0))
        return max(0.0, min(1.0, value / max_score))
    old_key, old_max = LEGACY_DIM_FIELDS.get(key, (None, None))
    if old_key and old_key in dims:
        value = float(dims.get(old_key, 0))
        return max(0.0, min(1.0, value / old_max))
    return 0.0


def dim_ratios(record: dict) -> list[float]:
    dims = record.get("dimension_scores") or {}
    return [dim_ratio(dims, key, max_score) for key, max_score, _weight in DIM_FIELDS]


def sample_fidelity(record: dict) -> float:
    ratios = dim_ratios(record)
    weighted = sum(ratio * weight for ratio, (_key, _max_score, weight) in zip(ratios, DIM_FIELDS))
    deficits = [max(0.0, 0.6 - ratio) for ratio in ratios]
    mean_penalty = sum(deficits) / len(deficits)
    max_penalty = max(deficits) if deficits else 0.0
    return max(0.0, weighted - 0.25 * mean_penalty - 0.15 * max_penalty)


def sample_noise(record: dict) -> float:
    dims = record.get("dimension_scores") or {}
    return dim_ratio(dims, NOISE_FIELD, 10)


def sample_completed(record: dict) -> bool:
    return sample_noise(record) > 0.10


def sample_severe(record: dict) -> bool:
    ratios = dim_ratios(record)
    tags = {str(tag) for tag in record.get("error_tags", []) or []}
    return (
        sample_fidelity(record) < 0.35
        or sample_noise(record) <= 0.10
        or float(record.get("score_0_100", 0)) < 40
        or any(ratio < 0.2 for ratio in ratios)
        or "code_added_removed_or_rewritten" in tags
    )


def sample_direct_usable(record: dict) -> bool:
    ratios = dim_ratios(record)
    return (
        float(record.get("score_0_100", 0)) > 75
        and sample_noise(record) > 0.60
        and min(ratios) >= 0.50
    )


def sample_subjective_adjustment(record: dict) -> float:
    value = record.get("subjective_adjustment_m5_p4", record.get("subjective_adjustment", 0))
    try:
        parsed = float(value or 0)
    except (TypeError, ValueError):
        parsed = 0.0
    return max(-5.0, min(4.0, parsed))


def dimension_average(records: list[dict], total_samples: int, key: str, max_score: int) -> float:
    if total_samples <= 0:
        return 0.0
    total = 0.0
    for record in records:
        dims = record.get("dimension_scores") or {}
        total += dim_ratio(dims, key, max_score)
    return total / total_samples


def llm_dimension_score(records: list[dict], total_samples: int) -> tuple[float, dict[str, float]]:
    dimension_avgs = {
        key: dimension_average(records, total_samples, key, max_score)
        for key, max_score, _weight in SCORE_DIM_FIELDS
    }
    score = 100 * sum(
        weight * (dimension_avgs[key] ** DIMENSION_POWER)
        for key, _max_score, weight in SCORE_DIM_FIELDS
    )
    return score, dimension_avgs


def tag_counts(records: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for tag in record.get("error_tags", []) or []:
            counts[str(tag)] = counts.get(str(tag), 0) + 1
    return counts


def score_records(records: list[dict], total_samples: int) -> dict:
    scores = [float(record.get("score_0_100", 0)) for record in records]
    neds = [float(record["ned"]) for record in records if record.get("ned") is not None]
    fidelity_sum = sum(sample_fidelity(record) for record in records)
    noise_sum = sum(sample_noise(record) for record in records)
    direct_usable_count = sum(1 for record in records if sample_direct_usable(record))
    completed_count = sum(1 for record in records if sample_completed(record))
    severe_count = (total_samples - len(records)) + sum(1 for record in records if sample_severe(record))
    subjective_adjustment_sum = sum(sample_subjective_adjustment(record) for record in records)

    denominator = total_samples
    fidelity_score = fidelity_sum / denominator
    noise_score = noise_sum / denominator
    direct_usable_rate = direct_usable_count / denominator
    completion_rate = completed_count / denominator
    safety_score = max(0.0, 1.0 - severe_count / denominator)

    llm_score, dimension_avgs = llm_dimension_score(records, total_samples)
    subjective_adjustment_avg = subjective_adjustment_sum / denominator
    counts = tag_counts(records)
    return {
        "records": len(records),
        "total_samples": total_samples,
        "missing_records": total_samples - len(records),
        "avg_llm_score": sum(scores) / len(scores) if scores else None,
        "trimmed_avg_llm_score": trimmed_mean(scores),
        "avg_ned": sum(neds) / len(neds) if neds else None,
        "fidelity_score_pct": fidelity_score * 100,
        "noise_usability_pct": noise_score * 100,
        "direct_usable_rate_pct": direct_usable_rate * 100,
        "completion_rate_pct": completion_rate * 100,
        "safety_score_pct": safety_score * 100,
        "severe_count": severe_count,
        "llm_dimension_score_v4": llm_score,
        "dimension_averages": dimension_avgs,
        "subjective_adjustment_avg": subjective_adjustment_avg,
        "final_score_v4": llm_score,
        "top_error_tags": sorted(counts.items(), key=lambda item: item[1], reverse=True)[:8],
    }


def score_run(path: Path, total_samples: int, file_to_category: dict[str, str], category_counts: dict[str, int]) -> dict:
    records = load_jsonl(path)
    unknown = sorted({image_file_name(record) for record in records if image_file_name(record) not in file_to_category})
    if unknown:
        raise RuntimeError(f"{path}: missing category mapping for {unknown[:10]}")

    row = {
        "run": infer_run_name(path),
        "prompt_policy": infer_prompt_policy(path.name),
        "judge_file": str(path.resolve().relative_to(ROOT)).replace("\\", "/"),
        **score_records(records, total_samples),
    }
    row["prompt_group"] = prompt_group(row["prompt_policy"])

    categories = {}
    category_scores = []
    weighted_category_score = 0.0
    for category, count in category_counts.items():
        if category not in CATEGORY_WEIGHTS:
            raise RuntimeError(f"missing category weight for {category}")
        category_records = [record for record in records if file_to_category[image_file_name(record)] == category]
        scored = score_records(category_records, count)
        scored["category"] = category
        scored["category_weight_v4"] = CATEGORY_WEIGHTS[category]
        categories[category] = scored
        category_scores.append(scored["final_score_v4"])
        weighted_category_score += CATEGORY_WEIGHTS[category] * scored["final_score_v4"]
    row["categories"] = categories
    row["global_llm_dimension_score_v4"] = row["final_score_v4"]
    row["category_macro_score_v4"] = sum(category_scores) / len(category_scores) if category_scores else None
    row["category_min_score_v4"] = min(category_scores) if category_scores else None
    if category_scores:
        mean = sum(category_scores) / len(category_scores)
        row["category_std_v4"] = math.sqrt(sum((score - mean) ** 2 for score in category_scores) / len(category_scores))
    else:
        row["category_std_v4"] = None
    row["final_score_v4"] = max(0.0, min(100.0, weighted_category_score))
    return row


def fmt(value, digits: int = 2) -> str:
    if value is None:
        return "-"
    return f"{value:.{digits}f}"


def write_markdown(path: Path, rows: list[dict]) -> None:
    def append_ranking_table(title: str, group_rows: list[dict]) -> None:
        lines.extend([
            "",
            f"## {title}",
            "",
            "| 方案 | 提示词 | 记录 | 最终积分 v4 | 全局六维分 | 类别宏平均 | 最弱类别 | 类别标准差 | 保真度诊断 | 噪声可用性 | 严格可用率 | 完成率 | 安全分 | severe | 平均 LLM | 平均 NED |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ])
        for row in group_rows:
            lines.append(
                "| {run} | {prompt} | {records}/{total} | {final} | {global_score} | {macro} | {min_score} | {std} | {fidelity}% | {noise}% | {usable}% | {completion}% | {safety}% | {severe} | {avg_llm} | {avg_ned} |".format(
                    run=row["run"],
                    prompt=row["prompt_policy"],
                    records=row["records"],
                    total=row["total_samples"],
                    final=fmt(row["final_score_v4"]),
                    global_score=fmt(row["global_llm_dimension_score_v4"]),
                    macro=fmt(row["category_macro_score_v4"]),
                    min_score=fmt(row["category_min_score_v4"]),
                    std=fmt(row["category_std_v4"]),
                    fidelity=fmt(row["fidelity_score_pct"]),
                    noise=fmt(row["noise_usability_pct"]),
                    usable=fmt(row["direct_usable_rate_pct"]),
                    completion=fmt(row["completion_rate_pct"]),
                    safety=fmt(row["safety_score_pct"]),
                    severe=row["severe_count"],
                    avg_llm=fmt(row["avg_llm_score"]),
                    avg_ned=fmt(row["avg_ned"], 4),
                )
            )

    lines = [
        "# Benchmark v4 Results",
        "",
        "按 `benchmark_guide_v4.md` 规则从 LLM 六维评分结果重算。最终排序使用分类加权后的 `final_score_v4`。",
        "",
        "为避免提示词策略混排，主排名分为短提示榜和长/严格提示榜；全部结果表只作诊断对照。",
    ]
    short_rows = [row for row in rows if row["prompt_group"] == "short_prompt"]
    long_rows = [row for row in rows if row["prompt_group"] == "long_or_strict_prompt"]
    other_rows = [row for row in rows if row["prompt_group"] == "other_prompt"]
    append_ranking_table("短提示榜 `<image>OCR:`", short_rows)
    append_ranking_table("长/严格提示榜", long_rows)
    if other_rows:
        append_ranking_table("其他提示/接口口径", other_rows)
    append_ranking_table("全部结果诊断表（不作混排排名）", rows)
    for row in rows:
        lines.extend(["", f"## {row['run']}", ""])
        lines.extend([
            "| 类别 | 权重 | 记录 | final_score_v4 | 保真度诊断 | 噪声可用性 | 严格可用率 | 完成率 | 安全分 | severe | 高频错误 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ])
        for category, scored in row["categories"].items():
            tags = ", ".join(f"{tag}:{count}" for tag, count in scored["top_error_tags"][:5])
            lines.append(
                "| {category} | {weight}% | {records}/{total} | {final} | {fidelity}% | {noise}% | {usable}% | {completion}% | {safety}% | {severe} | {tags} |".format(
                    category=category,
                    weight=fmt(scored["category_weight_v4"] * 100),
                    records=scored["records"],
                    total=scored["total_samples"],
                    final=fmt(scored["final_score_v4"]),
                    fidelity=fmt(scored["fidelity_score_pct"]),
                    noise=fmt(scored["noise_usability_pct"]),
                    usable=fmt(scored["direct_usable_rate_pct"]),
                    completion=fmt(scored["completion_rate_pct"]),
                    safety=fmt(scored["safety_score_pct"]),
                    severe=scored["severe_count"],
                    tags=tags or "-",
                )
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        "run",
        "prompt_group",
        "prompt_policy",
        "records",
        "total_samples",
        "missing_records",
        "final_score_v4",
        "global_llm_dimension_score_v4",
        "llm_dimension_score_v4",
        "fidelity_score_pct",
        "noise_usability_pct",
        "direct_usable_rate_pct",
        "completion_rate_pct",
        "safety_score_pct",
        "severe_count",
        "category_macro_score_v4",
        "category_min_score_v4",
        "category_std_v4",
        "avg_llm_score",
        "trimmed_avg_llm_score",
        "avg_ned",
        "judge_file",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fields})


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Benchmark v4 tables from LLM judge JSONL files.")
    parser.add_argument("--eval-dir", type=Path, default=EVAL_DIR)
    parser.add_argument("--pattern", default="llm_judge_*_full100_*_deepseek_v4_flash_v4.jsonl")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--total-samples", type=int, default=TOTAL_SAMPLES)
    parser.add_argument("--out-json", type=Path, default=EVAL_DIR / "benchmark_v4_results.json")
    parser.add_argument("--out-csv", type=Path, default=EVAL_DIR / "benchmark_v4_results.csv")
    parser.add_argument("--out-md", type=Path, default=EVAL_DIR / "benchmark_v4_results.md")
    parser.add_argument("--include-incomplete", action="store_true", help="Include judge files with fewer records than --total-samples.")
    args = parser.parse_args()

    file_to_category, category_counts = load_manifest(args.manifest)
    paths = sorted(args.eval_dir.glob(args.pattern))
    rows = []
    skipped = []
    for path in paths:
        row = score_run(path, args.total_samples, file_to_category, category_counts)
        if not args.include_incomplete and row["records"] < row["total_samples"]:
            skipped.append(row)
            continue
        rows.append(row)
    rows.sort(key=lambda row: row["final_score_v4"], reverse=True)

    args.out_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(args.out_csv, rows)
    write_markdown(args.out_md, rows)
    print(json.dumps({"runs": len(rows), "skipped_incomplete": len(skipped), "out_md": str(args.out_md), "top": rows[:3]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
