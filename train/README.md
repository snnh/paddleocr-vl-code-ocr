# 训练说明

公开仓库不发布训练图片，但提供模型 v6 的可执行训练入口、数据格式、泄漏检查、配置生成和启动命令。入口默认只做预检和生成配置，必须显式加入 `--run` 才会启动训练。

## 训练目标

基于 PaddleOCR-VL-1.6 微调开发场景代码 OCR 模型，使其更适合：

- IDE / 编辑器代码截图。
- 终端输出和命令。
- Traceback 与报错日志。
- YAML / JSON / TOML / INI 配置。
- Git diff、文档代码块和 API 表格。
- 小字号、暗色主题、压缩和拍屏困难样本。

## 训练策略

- 基础模型：PaddleOCR-VL-1.6。
- 微调方式：LoRA。
- 训练提示词：`<image>OCR:`。
- 输出目标：只输出图片中可见文字。
- 模型版本：v6。
- 训练数据：冻结快照共 1102 条；训练数据不随公开仓库发布。
- 测试集：Benchmark v5 内容版本 5.2，共 304 题，不参与训练和训练期调参。
- 防泄漏：冻结审计中训练集与测试集图片 SHA-256 重叠为 0。

## 参数摘要

关键参数见：

```text
train/paddleocr_vl_code_ocr_lora_config_summary.yaml
```

该文件是公开摘要，不是完整训练 notebook。

## 数据格式

训练入口同时接受 JSON 数组和 JSONL。每条记录包含一张图片、固定提示词和人工真值：

```json
{
  "images": ["images/example.png"],
  "messages": [
    {"role": "user", "content": "<image>OCR:"},
    {"role": "assistant", "content": "图片中可见的原始文字"}
  ]
}
```

图片路径可相对于数据文件、当前目录或仓库根目录。训练、验证和最终评估集会按图片 SHA-256 检查重叠；`--final-eval-data` 只参与泄漏检查，绝不会写入训练配置。

## 公开训练入口

先按照 PaddlePaddle 与 PaddleFormers 官方说明安装与 CUDA 匹配的训练环境，并确认 `paddleformers-cli` 可用。建议使用独立 Linux/NVIDIA GPU 环境，避免和 vLLM 推理依赖混装。

本入口复现本项目决赛模型实际采用的 PaddleFormers 训练栈。PaddleOCR 后续版本的官方文档可能推荐 ERNIEKit；若切换训练框架，应作为新的复现实验记录，不能与本项目 v6 配置混写。

先执行安全预检：

```powershell
python -B .\train\train_paddleocr_vl_code_ocr.py `
  --train-data <train.json或train.jsonl> `
  --dev-data <独立验证集，可选> `
  --final-eval-data <最终评估集，仅用于防泄漏检查>
```

预检会验证消息格式、提示词、图片存在性、空真值、批内重复和跨集合 SHA-256 重叠，并在 `outputs/training_config/` 生成可审阅的 YAML。确认无误后启动训练：

```powershell
python -B .\train\train_paddleocr_vl_code_ocr.py `
  --train-data <train.json或train.jsonl> `
  --dev-data <独立验证集，可选> `
  --final-eval-data <最终评估集，仅用于防泄漏检查> `
  --run
```

该入口固定复现决赛 v6 参数：PaddleOCR-VL-1.6、LoRA rank 8、`max_seq_len=16384`、batch 1、梯度累积 2、2 epochs、学习率 `2e-4`、min lr `2e-5`、warmup `0.1`、weight decay `0.01`、Adam beta2 `0.95`、seed 23。训练数据不公开，因此外部复现需要自行准备遵循相同格式和标注规范的数据。

## 同口径结果

Benchmark v5 内容版本 5.2 使用同一短提示和同一非思考裁判口径。官方 API 与本地 vLLM 的服务路径不同，所以该表用于展示最终方案的实际效果，不作为单变量训练消融。

| 方案 | 最终积分 | 全局均值 | 严格可用率 | 安全分 | 平均 NED |
| --- | ---: | ---: | ---: | ---: | ---: |
| PaddleOCR-VL-1.6 官方 API | 40.1408 | 62.3878 | 25.6579% | 80.2632% | 0.2660 |
| 本地微调模型 v6 | **58.4427** | **73.3494** | **38.1579%** | **90.7895%** | **0.1744** |
| 差值 | **+18.3019** | **+10.9616** | **+12.5000 个百分点** | **+10.5263 个百分点** | **-0.0916** |
