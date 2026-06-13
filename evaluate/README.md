# 评估说明

本目录包含开发场景代码 OCR benchmark 的评估脚本。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `evaluate_openai_compatible_vl_testset.py` | 调用 OpenAI-compatible 多模态接口生成 OCR 预测。 |
| `judge_ocr_predictions_llm.py` | 使用 LLM 对 OCR 预测进行六维评分。 |
| `build_benchmark_v4.py` | 汇总 benchmark v4 分类分和最终分。 |

## 基本流程

```text
测试集 JSONL
  |
模型生成 OCR 预测
  |
LLM 六维裁判
  |
benchmark v4 汇总
```

## 复现提示

- OCR 主提示词使用 `<image>OCR:`。
- 推理建议显式设置 `temperature=0`。
- 评估集不参与训练和训练期调参。
- 不同提示词策略应分榜展示，不建议混排。

