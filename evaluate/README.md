# 评估说明

本目录提供开发场景 OCR 的推理、LLM 裁判和计分脚本。v4 文件用于历史复现，当前评测入口为 Benchmark v5。

## 文件

| 文件 | 用途 |
| --- | --- |
| `evaluate_openai_compatible_vl_testset.py` | 调用 OpenAI-compatible 多模态接口生成 OCR 预测，支持断点续跑。 |
| `judge_ocr_predictions_llm.py` | 对人工真值和 OCR 预测进行六维 LLM 裁判。 |
| `build_benchmark_v5.py` | 按类别、难度和可靠性规则计算 `final_score_v5`。 |
| `build_benchmark_v4.py` | 历史 v4 计分脚本。 |

## 准备数据

公开仓库不包含冻结测试集。推理 JSONL 每条应包含图片路径、用户提示词和人工真值；v5 manifest 至少提供 `id`、`image`、`primary_category` 和 `difficulty_level`。

API key 只通过环境变量传入：

```powershell
$env:OPENAI_API_KEY="你的密钥或本地服务占位值"
```

## 运行流程

先用 1 条样本检查服务、图片编码、提示词和响应解析，再运行完整测试集。

```powershell
python -B .\evaluate\evaluate_openai_compatible_vl_testset.py --data-path .\test.jsonl --url <ocr-api-url> --model <ocr-model-id> --output .\evaluations\predictions.jsonl --summary .\evaluations\predictions_summary.json --errors .\evaluations\predictions_errors.jsonl --eval-prompt "<image>OCR:" --max-tokens 4096 --repetition-penalty 1.08 --temperature 0 --limit 1
```

去掉 `--limit 1` 后完成推理，再调用用户确认的裁判模型和 API：

```powershell
python -B .\evaluate\judge_ocr_predictions_llm.py --input .\evaluations\predictions.jsonl --url <judge-api-url> --model <judge-model-id> --output .\evaluations\judge.jsonl --summary .\evaluations\judge_summary.json --errors .\evaluations\judge_errors.jsonl --reasoning-object-effort none --workers 2
```

最后计分：

```powershell
python -B .\evaluate\build_benchmark_v5.py --manifest .\testset\manifest.jsonl --predictions .\evaluations\predictions.jsonl --judge .\evaluations\judge.jsonl --summary .\benchmark_outputs\summary.json --samples-output .\benchmark_outputs\samples.jsonl --report .\benchmark_outputs\report.md --run-name <run-name>
```

## 发布检查

- 预测、裁判和 manifest 的唯一图片数符合预期。
- 缺失、空输出和错误请求均显式记录。
- 模型 ID、提示词、采样参数、裁判和 reasoning 模式写入报告。
- 不混合不同测试集、提示词或裁判口径。
- 输出文件不含 API key、内网地址或本地绝对路径。

完整积分规则见 [../docs/benchmark_guide_v5.md](../docs/benchmark_guide_v5.md)。
