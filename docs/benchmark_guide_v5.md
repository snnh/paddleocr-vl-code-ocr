# OCR Benchmark v5 评测规则

更新时间：2026-07-16

Benchmark 名称固定为 v5，当前测试内容版本为 5.2。v5.2 使用 304 题冻结测试集；不同内容版本、提示词组或裁判口径不得直接混排。

## 数据集口径

- 数据集 ID：`code_ocr_eval_benchmark_v5_content_5_2_photo30_20260710`。
- 样本数：304。
- 类别：P01-P09，权重依次为 `15% / 8% / 15% / 12% / 10% / 8% / 12% / 8% / 12%`。
- 难度：simple 63、medium 156、hard 85。
- 主提示词组：`<image>OCR:`。
- 测试集不参与训练或训练期调参。

Manifest 至少提供 `id`、`image`、`primary_category` 和 `difficulty_level`。预测和裁判记录以规范化后的图片路径关联；缺失记录按 0 分并计入可靠性扣分。

## 六维 LLM 裁判

裁判只比较人工真值与模型预测，不读取 NED，也不根据代码语义补全内容。正式榜单使用 `dev_ocr_judge_v5_compat` 提示词和统一裁判模型；本项目正式结果使用 `tencent/hy3:free`，reasoning 关闭。medium reasoning 只用于争议样本复核，不替换正式记录。

| 维度 | 权重 | 检查内容 |
| --- | ---: | --- |
| 内容覆盖 | 18% | 主要可见内容是否完整 |
| 符号准确 | 24% | 标识符、数字、大小写、路径和代码符号 |
| 缩进对齐 | 16% | 缩进、嵌套、列表和表格对齐 |
| 结构格式 | 16% | 换行、代码块、区域和表格结构 |
| 阅读顺序 | 10% | 多区域和多文本块顺序 |
| 噪声与可用性 | 16% | 幻觉、重复、解释、包装和代码改写 |

样本分使用各维度归一化分数的 1.35 次幂加权：

```text
sample_score = 100 * sum(weight_i * (dimension_i / 10)^1.35)
```

## 最终积分

每个类别先计算样本均值，再按类别权重汇总。simple 基础题、medium/hard severe 比例以及整体可靠性只产生扣分：

```text
raw_score_v5 =
  category_weighted_score_v5
- simple_penalty_v5
- medium_risk_penalty_v5
- hard_risk_penalty_v5

final_score_v5 = clamp(raw_score_v5 - reliability_penalty_v5, 0, 100)
```

Severe Badcase 包括缺失、主要内容或符号严重漏错、结构崩坏、拒识、幻觉、重复输出、代码增删改写，以及输出远长于真值且噪声严重等情况。完成率、安全分、严格可用率和 NED 作为诊断指标展示。

## 复现流程

测试集不在公开仓库中，使用者需准备兼容 JSONL 和 manifest，并通过命令行显式提供模型、服务和输出路径：

```powershell
python -B .\evaluate\evaluate_openai_compatible_vl_testset.py --data-path .\test.jsonl --url <ocr-api-url> --model <ocr-model-id> --output .\evaluations\predictions.jsonl --summary .\evaluations\predictions_summary.json --errors .\evaluations\predictions_errors.jsonl --eval-prompt "<image>OCR:" --max-tokens 4096 --repetition-penalty 1.08 --temperature 0

python -B .\evaluate\judge_ocr_predictions_llm.py --input .\evaluations\predictions.jsonl --url <judge-api-url> --model <judge-model-id> --output .\evaluations\judge.jsonl --summary .\evaluations\judge_summary.json --errors .\evaluations\judge_errors.jsonl --reasoning-object-effort none

python -B .\evaluate\build_benchmark_v5.py --manifest .\testset\manifest.jsonl --predictions .\evaluations\predictions.jsonl --judge .\evaluations\judge.jsonl --summary .\benchmark_outputs\summary.json --samples-output .\benchmark_outputs\samples.jsonl --report .\benchmark_outputs\report.md --run-name <run-name> --dataset-version code_ocr_eval_benchmark_v5_content_5_2_photo30_20260710 --content-version 5.2
```

API key 仅通过环境变量传入，不写入命令历史、脚本、报告或 JSONL。正式发布前必须核验预期样本数、唯一图片数、空输出、缺失记录、裁判模型、提示词版本和 reasoning 模式。

## 榜单分组

- `<image>OCR:` 短提示为主榜。
- 模型官方推荐提示词单独成组。
- v4 作为历史 Benchmark 保留，不与 v5.2 比较。
- 分差低于 0.5 时不作显著领先结论。
