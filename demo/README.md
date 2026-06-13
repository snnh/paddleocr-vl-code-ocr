# Demo 说明

本目录提供一个最小 OpenAI-compatible 多模态接口示例，用于调用本地 vLLM 或兼容服务进行开发场景 OCR。

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

