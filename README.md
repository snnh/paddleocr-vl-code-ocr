# PaddleOCR-VL 开发场景代码 OCR

本项目基于 PaddleOCR-VL-1.6 微调开发场景 OCR 模型，面向 IDE、终端、Traceback、配置文件、Git diff、文档代码块、API 表格和多区域开发界面。目标不是生成或修复代码，而是忠实转写图片中的可见文字。

当前模型版本为 v6，决赛技术方案已冻结。Benchmark 名称保持 v5，当前测试内容版本为 5.2。

## 当前版本

| 项目 | 口径 |
| --- | --- |
| 基础模型 | `PaddlePaddle/PaddleOCR-VL-1.6` |
| 模型版本 | v6 |
| 训练数据 | 1102 条；不随仓库发布 |
| 提示词 | `<image>OCR:` |
| 推荐推理参数 | `max_tokens=4096, repetition_penalty=1.08, temperature=0` |
| Benchmark | v5，内容版本 5.2，304 题 |
| 最终积分 | `final_score_v5=58.4427` |
| 训练复现 | [公开训练入口](train/README.md)，默认预检，显式 `--run` 才启动 |
| 模型权重 | [Hugging Face](https://huggingface.co/snnh/paddleocr_vl_code_ocr) |
| 在线演示 | [Hugging Face Space](https://huggingface.co/spaces/snnh/paddleocr-vl-code-ocr-demo) |

## 为什么单独做开发场景 OCR

代码截图中的括号、引号、路径、缩进、换行、表格列和 diff 前缀都具有实际含义。普通 OCR 或通用 VLM 即使读懂内容，也可能加入解释、补全不可见代码或改变结构，使结果无法直接复制、搜索和排错。本项目重点控制这些错误：

- 保留大小写、符号、缩进、换行和阅读顺序；
- 不解释、不总结、不修复、不补全；
- 减少 Markdown 包装、重复输出、幻觉和代码改写；
- 提高小字号、暗色主题、拍屏和多区域画面的稳定性。

## Benchmark v5.2 摘要

测试集固定为 304 题，覆盖 P01-P09 九类开发场景，难度分布为 simple 63、medium 156、hard 85。测试集不参与训练或训练期调参；冻结审计中训练集与测试集图片 SHA-256 重叠为 0。

| 模型 | 提示词组 | 记录 | 最终积分 | 完成率 | 安全分 | 平均 NED |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR-VL-1.6 本地模型 v6 | `<image>OCR:` | 304/304 | **58.4427** | 99.0132% | 90.7895% | 0.1744 |
| StepFun step-3.7-flash (high) | `<image>OCR:` | 304/304 | 57.3628 | 97.6974% | 79.2763% | 0.2481 |
| PaddleOCR-VL-1.6 官方 API | `<image>OCR:` | 303/304 | 40.1408 | 98.0263% | 80.2632% | 0.2660 |

完整口径与结果见 [Benchmark v5 规则](docs/benchmark_guide_v5.md) 和 [Benchmark v5 榜单](docs/ocr_benchmark_v5.md)。v4 结果保留为历史记录，不与 v5.2 混排。

## 仓库结构

```text
.
├── dataset/                  # 数据格式和质检脚本
├── demo/                     # OpenAI-compatible 单图 Demo
├── docs/                     # 数据声明、评测规则和榜单
├── evaluate/                 # 推理、LLM 裁判和 v4/v5 计分脚本
├── skills/ocr-benchmark/     # 可复用的 Codex OCR Benchmark skill
├── train/                    # 可执行训练入口、数据格式与参数摘要
├── MODEL_CARD.md
└── app.py
```

## 快速试用

先启动本地 vLLM 或其他 OpenAI-compatible 多模态服务，然后设置：

```powershell
$env:OPENAI_API_KEY="本地服务可使用占位值"
$env:OPENAI_BASE_URL="http://localhost:8000/v1/chat/completions"
$env:MODEL_NAME="你的模型名"
python .\app.py --image .\examples\sample.png
```

公开仓库不包含训练图片、评估集图片、模型权重或 API key。完整评测流程见 [evaluate/README.md](evaluate/README.md)。

## 训练复现

训练图片不公开，但仓库提供可执行的 PaddleOCR-VL-1.6 LoRA 入口。它支持 JSON/JSONL 消息格式，启动前检查图片、真值和跨集合 SHA-256 重叠，并生成与模型 v6 一致的训练配置：

```powershell
python -B .\train\train_paddleocr_vl_code_ocr.py --train-data <train.json> --final-eval-data <test.jsonl>
```

默认命令不会训练；检查生成的 YAML 后加入 `--run` 才会调用 `paddleformers-cli train`。数据格式、独立验证集和环境要求见 [训练说明](train/README.md)。

## OCR Benchmark Skill

仓库内 [skills/ocr-benchmark](skills/ocr-benchmark/SKILL.md) 可用于运行、续跑、裁判、计分、审计和发布可配置的 OCR Benchmark。首次使用会询问裁判模型 ID 和 API URL；测试集、报告目录与排行目录均可单独配置。

将目录复制到 Codex skills 目录即可安装：

```powershell
Copy-Item .\skills\ocr-benchmark "$env:USERPROFILE\.codex\skills" -Recurse -Force
```

## 数据与许可

训练数据和测试集不随本仓库重新分发。构建方式、人工标注和防泄漏检查见 [训练数据构建报告](docs/训练数据构建报告.md) 与 [数据声明](docs/data_statement.md)。代码、脚本、配置摘要和文档按 [Apache License 2.0](LICENSE) 开源；第三方素材仍受各自来源许可约束，详见 [NOTICE](NOTICE)。

## 局限性

模型仍可能在复杂 API 表格、长 Traceback、多区域截图、极小字号、模糊拍屏、深层嵌套配置和罕见符号上出错。输出用于 OCR 转写，不应直接作为可执行代码或安全决策依据。
