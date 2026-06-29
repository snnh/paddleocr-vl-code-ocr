# PaddleOCR-VL 开发场景代码 OCR

本仓库是 PaddleOCR 全球衍生模型挑战赛使用的公开项目仓库，根目录展示项目入口，`dataset/` 放数据构建与说明，`train/` 放训练策略摘要，`evaluate/` 放评估脚本，`demo/` 放最小演示，`docs/` 放详细文档。

> 当前初赛提交候选为 v6。模型、文档和 benchmark 已按 2026-06-19 版本同步。

## 在线 Demo

🤗 **Hugging Face Space**：[paddleocr-vl-code-ocr-demo](https://huggingface.co/spaces/snnh/paddleocr-vl-code-ocr-demo)

上传一张开发场景截图（IDE / 终端 / Traceback / 配置 / Git diff / API 表格 / 困难样本），即可在线体验微调模型的 OCR 输出。Space 使用免费 CPU 硬件，仅作为可访问演示入口；首次加载需拉取模型权重，单图可能需要 1-5 分钟。benchmark 分数和正式复现口径以本地 GPU / OpenAI-compatible 接口结果为准。

## 任务目标

项目基于 PaddleOCR-VL-1.6，面向 IDE、终端、Traceback、配置文件、Git diff、文档代码块、API 表格和困难样本等开发场景 OCR。

普通 OCR 在代码场景中常见问题包括符号识别错误、缩进丢失、结构错乱、解释性输出、不可见补全和代码改写。本项目希望模型更稳定地做到：

- 只输出图片中可见文字。
- 保留代码符号、大小写、缩进、换行和阅读顺序。
- 减少幻觉、解释性包装和擅自补全。
- 提高终端、Traceback、配置、Diff、API 表格等开发场景的可用性。

推荐提示词：

```text
<image>OCR:
```

## 当前状态

| 项 | 状态 |
| --- | --- |
| 基础模型 | PaddleOCR-VL-1.6 |
| 任务方向 | 代码文字识别 / 开发场景 OCR |
| 训练状态 | 初赛提交候选 v6 |
| 测试集 | benchmark v4，100 题冻结测试集 |
| 推荐推理口径 | `max_tokens=4096, repetition_penalty=1.08, temperature=0` |
| 模型发布 | https://huggingface.co/snnh/paddleocr_vl_code_ocr |

benchmark 见 [docs/ocr_benchmark_v4.md](docs/ocr_benchmark_v4.md)。当前 v6 在 benchmark v4 固定 100 题上最终积分为 `61.08`。

提交材料统一口径：

- 最终候选：PaddleOCR-VL-1.6 微调 v6。
- 主提示词：`<image>OCR:`。
- 主 benchmark：benchmark v4 固定 100 题，`final_score_v4=61.08`。
- 推荐推理：`max_tokens=4096, repetition_penalty=1.08, temperature=0`。
- 在线 Space：仅用于展示模型可访问性，不作为 benchmark 性能依据。

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
