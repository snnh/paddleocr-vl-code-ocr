# PaddleOCR-VL 开发场景代码 OCR

本仓库是 PaddleOCR 全球衍生模型挑战赛使用的公开项目仓库，目标是把 PaddleOCR-VL 微调成更适合开发场景的结构保真 OCR 模型。输入是 IDE、终端、Traceback、配置文件、Git diff、文档代码块、API 表格和困难样本截图，输出只包含图片中可见文字。

这个任务不是通用代码生成，也不是普通文本 OCR。开发场景 OCR 对符号、缩进、换行、路径、表格列、diff 前缀、错误栈顺序和多区域阅读顺序敏感；一个括号、空格、行号或 `+/-` 前缀错误，都可能让 OCR 结果无法复制、搜索或复现问题。

> 当前初赛提交候选为 v6。模型、文档和 benchmark 已按 2026-06-19 版本同步。

## 提交口径

| 项 | 当前提交 |
| --- | --- |
| 基础模型 | PaddleOCR-VL-1.6 |
| 微调版本 | v6 初赛提交候选 |
| 任务方向 | 开发场景代码 OCR / 结构保真文字转写 |
| 主提示词 | `<image>OCR:` |
| 主 benchmark | benchmark v4，100 题冻结测试集 |
| v6 分数 | `final_score_v4=61.08` |
| 推荐推理 | `max_tokens=4096, repetition_penalty=1.08, temperature=0` |
| 模型权重 | https://huggingface.co/snnh/paddleocr_vl_code_ocr |
| 在线演示 | https://huggingface.co/spaces/snnh/paddleocr-vl-code-ocr-demo |

## 在线 Demo

🤗 **Hugging Face Space**：[paddleocr-vl-code-ocr-demo](https://huggingface.co/spaces/snnh/paddleocr-vl-code-ocr-demo)

上传一张开发场景截图（IDE / 终端 / Traceback / 配置 / Git diff / API 表格 / 困难样本），即可在线体验微调模型的 OCR 输出。Space 使用免费 CPU 硬件，仅作为可访问演示入口；首次加载需拉取模型权重，单图可能需要 1-5 分钟。benchmark 分数和正式复现口径以本地 GPU / OpenAI-compatible 接口结果为准。

## 任务难点

本项目聚焦普通 OCR 和通用 VLM 在开发截图中容易失效的长尾问题：

- **符号密集**：代码标点、路径分隔符、命令参数、`=>`、`::`、`[]`、`{}` 等容易被漏识别或替换。
- **结构敏感**：Python/YAML/Markdown/树状终端输出依赖缩进、换行和层级，字符对但结构错仍不可用。
- **多区域阅读顺序**：IDE 标签页、代码正文、终端、问题面板、diff hunk 和网页代码块经常同时出现。
- **开发语义约束**：OCR 不能解释、修复、补全或重写代码，只能转写图片里真实可见内容。
- **真实使用噪声**：暗色主题、小字号、压缩、拍屏、滚动区域、表格列错位和长 Traceback 都会显著降低可用性。

模型目标是稳定做到：

- 只输出图片中可见文字，不解释、不总结、不补全。
- 保留代码符号、大小写、缩进、换行、路径和阅读顺序。
- 减少 Markdown 包装、幻觉、重复输出和代码改写。
- 提高终端、Traceback、配置、Diff、API 表格等开发场景的复制可用性。

推荐提示词：

```text
<image>OCR:
```

## 材料入口

| 材料 | 链接 |
| --- | --- |
| 模型卡 | [MODEL_CARD.md](MODEL_CARD.md) |
| 训练策略摘要 | [train/README.md](train/README.md) |
| LoRA 参数摘要 | [train/paddleocr_vl_code_ocr_lora_config_summary.yaml](train/paddleocr_vl_code_ocr_lora_config_summary.yaml) |
| 数据构建报告 | [docs/训练数据构建报告.md](docs/训练数据构建报告.md) |
| 评估规则 | [docs/benchmark_guide_v4.md](docs/benchmark_guide_v4.md) |
| benchmark 结果 | [docs/ocr_benchmark_v4.md](docs/ocr_benchmark_v4.md) |
| OpenAI-compatible 评估脚本 | [evaluate/](evaluate/) |
| Demo 说明 | [demo/README.md](demo/README.md) |

## Benchmark 摘要

benchmark v4 使用 100 题冻结测试集，覆盖 8 类开发 OCR 场景，并按类别权重汇总 `final_score_v4`。测试集不参与训练和训练期调参。

| 模型 | 提示词 | final_score_v4 | 平均 LLM | 平均 NED | 严格可用率 | 完成率 | 安全分 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR-VL-1.6 微调 v6 | `<image>OCR:` | 61.08 | 74.05 | 0.1360 | 47.00% | 96.00% | 79.00% |

完整结果见 [docs/ocr_benchmark_v4.md](docs/ocr_benchmark_v4.md)。正式复现建议使用本地 GPU / vLLM / OpenAI-compatible 接口；HF Space 仅用于在线可访问演示。

## 仓库结构

```text
.
├── README.md
├── MODEL_CARD.md
├── LICENSE
├── NOTICE
├── requirements.txt
├── app.py
├── dataset/
│   ├── README.md
│   └── audit_dataset_quality.py
├── train/
│   ├── README.md
│   └── paddleocr_vl_code_ocr_lora_config_summary.yaml
├── evaluate/
│   ├── README.md
│   ├── evaluate_openai_compatible_vl_testset.py
│   ├── judge_ocr_predictions_llm.py
│   └── build_benchmark_v4.py
├── demo/
│   ├── README.md
│   └── openai_compatible_ocr_demo.py
└── docs/
    ├── task_description.md
    ├── data_statement.md
    ├── 训练数据构建报告.md
    ├── benchmark_guide_v4.md
    └── ocr_benchmark_v4.md
```

## 快速试用

本仓库提供 OpenAI-compatible 多模态接口示例。先设置环境变量：

```powershell
$env:OPENAI_API_KEY="你的密钥"
$env:OPENAI_BASE_URL="http://localhost:8000/v1/chat/completions"
$env:MODEL_NAME="你的模型名"
```

运行：

```powershell
python .\app.py --image .\examples\sample.png
```

也可以直接运行：

```powershell
python .\demo\openai_compatible_ocr_demo.py --image .\examples\sample.png
```

## 训练说明

公开仓库不放完整训练 notebook。训练策略、关键参数和复现口径整理在 [train/README.md](train/README.md)，参数摘要见 [train/paddleocr_vl_code_ocr_lora_config_summary.yaml](train/paddleocr_vl_code_ocr_lora_config_summary.yaml)。

## 评估复现

1. 准备符合 `dataset/README.md` 说明的测试集 JSONL。
2. 使用 `evaluate/evaluate_openai_compatible_vl_testset.py` 生成模型预测。
3. 使用 `evaluate/judge_ocr_predictions_llm.py` 进行六维 LLM 裁判。
4. 使用 `evaluate/build_benchmark_v4.py` 汇总 `final_score_v4`。

详细规则见 [docs/benchmark_guide_v4.md](docs/benchmark_guide_v4.md)。

## 数据说明

训练数据不随本公开仓库直接发布。评估集按比赛要求单独提交，可通过比赛邮件或数据集平台链接获取。数据构建方法、标注规范和质量控制流程见 [docs/训练数据构建报告.md](docs/训练数据构建报告.md)。

## 许可证

本仓库中的代码、脚本、配置摘要和文档默认按 [Apache License 2.0](LICENSE) 开源，除非具体文件另有说明。

Hugging Face 上发布的微调模型权重同样按 Apache License 2.0 开源。第三方数据集、训练/评估来源素材和比赛单独提交的评估集不随本仓库或模型权重重新分发、重新授权，仍受各自来源的许可、使用条款和限制约束。相关说明见 [NOTICE](NOTICE)。

## 局限性

当前模型仍可能在复杂 API 表格、长 Traceback、多区域截图、极小字号、模糊图片、深层嵌套配置和罕见符号上出错。模型只应用于 OCR 转写，不应作为代码生成或代码修复工具使用。
