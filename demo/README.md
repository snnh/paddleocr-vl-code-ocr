# Demo 说明

## 在线 Demo

🤗 [Hugging Face Space](https://huggingface.co/spaces/snnh/paddleocr-vl-code-ocr-demo)：上传开发场景截图即可在线体验，无需本地部署。该 Space 使用免费 CPU 硬件，仅作为可访问演示入口；首次加载需拉取模型权重，单图可能需要 1-5 分钟。benchmark 分数和正式复现以本地 GPU / OpenAI-compatible 接口结果为准。

## 本地 Demo

本目录提供一个最小 OpenAI-compatible 多模态接口示例，用于调用本地 vLLM 或兼容服务进行开发场景 OCR。

本地推荐推理口径与提交 benchmark 保持一致：`max_tokens=4096, repetition_penalty=1.08, temperature=0`。

## 环境变量

```powershell
$env:OPENAI_API_KEY="你的密钥"
$env:OPENAI_BASE_URL="http://localhost:8000/v1/chat/completions"
$env:MODEL_NAME="你的模型名"
```

## 运行

```powershell
python .\demo\openai_compatible_ocr_demo.py --image .\examples\sample.png
```

默认提示词为：

```text
<image>OCR:
```

输出应只包含图片中可见文字，不应解释、总结或补全不可见代码。
