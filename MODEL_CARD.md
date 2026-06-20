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

这是 PaddleOCR 全球衍生模型挑战赛提交用模型卡。本文档中文优先，必要英文术语仅用于模型平台兼容。

当前初赛提交候选为 v6。

## 模型简介

本模型基于 PaddleOCR-VL-1.6 微调，面向开发场景 OCR。目标是识别 IDE 截图、终端输出、Traceback、配置文件、Git diff、文档代码块、API 表格、小字号和暗色主题等开发相关图片中的可见文字。

推荐提示词：

```text
<image>OCR:
```

## 基础模型

- 基础模型：PaddleOCR-VL-1.6。
- 微调方式：LoRA 微调后导出合并模型。
- 目标任务：代码文字识别 / 开发工具 OCR。

## 数据概况

当前训练索引 `train.json` 共 1102 条样本。公开仓库不直接发布训练数据，只说明数据类型和质量控制方法。数据主要覆盖：

- IDE / 编辑器代码截图。
- 终端、Shell、PowerShell 命令和输出。
- Traceback、报错日志和诊断信息。
- YAML / JSON / TOML / INI 配置文件。
- Git diff、patch 和 PR 页面。
- Markdown / 文档代码块。
- API 表格、参数表和字段说明。
- 小字号、压缩、暗色主题、拍屏等困难样本。

最终 benchmark 测试集冻结，不参与训练和训练期调参。

## 使用场景

本模型适用于从开发场景截图中抽取可见文字，并尽量保留代码符号、缩进、换行、结构和阅读顺序。它不是代码修复或代码生成模型，不应补全图片中不可见的内容。

推荐解码参数：

```text
max_tokens=4096
repetition_penalty=1.08
temperature=0
```

## 阶段性评估

benchmark v4 包含 100 个样本，覆盖 8 类开发 OCR 场景。评估采用六维 LLM 裁判，并按类别权重汇总最终分。测试集不参与训练和训练期调参。

当前提交候选 v6 在 benchmark v4 上的结果：

| 指标 | 数值 |
| --- | ---: |
| final_score_v4 | 61.08 |
| 全局六维分 | 64.06 |
| 类别宏平均 | 63.86 |
| 最弱类别 | 44.54 |
| 严格可用率 | 47.00% |
| 完成率 | 96.00% |
| 安全分 | 79.00% |
| 平均 LLM | 74.05 |
| 平均 NED | 0.1360 |

完整 benchmark 与 demo 说明见 [GitHub docs/ocr_benchmark_v4.md](https://github.com/snnh/paddleocr-vl-code-ocr/blob/main/docs/ocr_benchmark_v4.md)。

## 局限性

模型在以下场景仍可能出错：

- 极小或模糊文本。
- 复杂 API 表格。
- 深层嵌套配置文件。
- 长 Traceback 输出。
- 多区域混排截图。
- 罕见符号、代码标点和缩进敏感内容。

模型输出应只作为 OCR 转写结果使用，不能视为代码语义理解或代码正确性保证。

## 许可说明

本 Hugging Face 仓库发布的微调模型权重按 Apache License 2.0 开源。GitHub 仓库中的代码、脚本、配置摘要和文档同样按 Apache License 2.0 开源，除非具体文件另有说明。

基础模型 PaddleOCR-VL-1.6 本身标注为 Apache-2.0。第三方数据集、训练/评估来源素材和比赛单独提交的评估集不随模型权重或 GitHub 仓库重新分发、重新授权，仍受各自来源的许可、使用条款和限制约束。

## 致谢

本模型为 PaddleOCR 全球衍生模型挑战赛构建，基础能力来自 PaddleOCR-VL 系列模型。
