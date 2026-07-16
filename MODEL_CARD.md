---
language:
- zh
- en
license: apache-2.0
base_model: PaddlePaddle/PaddleOCR-VL-1.6
pipeline_tag: image-text-to-text
tags:
- paddleocr
- ocr
- vision-language
- code-ocr
- developer-tools
---

# PaddleOCR-VL-1.6 开发场景代码 OCR 微调模型

本模型基于 PaddleOCR-VL-1.6 微调，面向 IDE、终端、Traceback、配置、Git diff、文档代码块、API 表格和多区域开发截图中的结构保真 OCR。当前模型版本为 v6，并作为 PaddleOCR 全球衍生模型挑战赛决赛冻结方案。

## 使用方法

推荐提示词：

```text
<image>OCR:
```

正式推理参数：

```text
max_tokens=4096
repetition_penalty=1.08
temperature=0
```

输出只应包含图片中的可见文字，不应解释、总结、补全或修复代码。不同提示词和采样参数可能显著改变输出风格与 Benchmark 结果。

## 训练概况

- 基础模型：`PaddlePaddle/PaddleOCR-VL-1.6`。
- 微调方式：LoRA 后导出合并模型。
- 训练提示词：`<image>OCR:`。
- 最大序列长度：16384。
- 训练快照：1102 条开发场景 OCR 样本。
- 数据范围：IDE、终端、报错日志、配置文件、diff、文档代码块、API 表格及困难画面。

训练数据不随模型或本仓库发布。模型 OCR 只用于预标注草稿，最终文本经过人工筛选或修订。冻结审计中训练集与 304 题测试集图片 SHA-256 重叠为 0。

## Benchmark v5.2

Benchmark v5 内容版本 5.2 共 304 题，覆盖 P01-P09 九类开发场景和 simple、medium、hard 三档难度。模型 v6 按正式参数完成 304/304 推理，并使用 `tencent/hy3:free`、reasoning 关闭的统一六维裁判口径计分。

| 指标 | 结果 |
| --- | ---: |
| `final_score_v5` | **58.4427** |
| 原始积分 | 60.3374 |
| 类别加权分 | 72.8633 |
| 全局样本均值 | 73.3494 |
| 严格可用率 | 38.1579% |
| 完成率 | 99.0132% |
| 安全分 | 90.7895% |
| 平均 NED | 0.1744 |

LLM 裁判存在约 `±0.5` 的展示误差。v5.2 不应与 v4、其他内容版本或不同提示词组直接混排。完整规则与对照结果见 [GitHub Benchmark v5](https://github.com/snnh/paddleocr-vl-code-ocr/blob/main/docs/ocr_benchmark_v5.md)。

## 适用场景

- 从 IDE、终端和调试工具截图中提取可搜索文本。
- 转写配置、日志、Traceback、diff 和 API 表格。
- 为开发文档归档、问题排查或辅助标注提供 OCR 草稿。

## 局限性

- 复杂 API 表格、长 Traceback、多区域界面和深层嵌套配置仍可能发生阅读顺序或结构错误。
- 极小字号、模糊拍屏、压缩伪影和罕见符号会降低准确率。
- 模型可能漏字、误认符号或重复文本；重要输出必须人工复核。
- 本模型用于转写，不应视为代码生成、代码修复或安全分析工具。

## 许可

模型权重和仓库代码按 Apache License 2.0 发布。第三方训练素材不随模型重新分发或重新授权，仍受各自许可和使用条款约束。

## 致谢

感谢 PaddleOCR 与 PaddlePaddle 社区提供基础模型、工具链和赛事平台。
