# 训练说明

公开仓库不放完整训练 notebook 或训练图片，仅保留模型 v6 的训练策略摘要和关键参数，便于评审理解技术路线。

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
