import argparse
import base64
import mimetypes
import os
from pathlib import Path

import requests


def image_to_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenAI-compatible OCR demo")
    parser.add_argument("--image", required=True, type=Path, help="输入图片路径")
    parser.add_argument("--prompt", default="<image>OCR:", help="OCR 提示词")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--repetition-penalty", type=float, default=1.10)
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "EMPTY")
    base_url = os.environ.get("OPENAI_BASE_URL", "http://localhost:8000/v1/chat/completions")
    model = os.environ.get("MODEL_NAME", "paddleocr-vl-code-ocr")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": args.prompt},
                    {"type": "image_url", "image_url": {"url": image_to_data_url(args.image)}},
                ],
            }
        ],
        "temperature": 0,
        "max_tokens": args.max_tokens,
        "extra_body": {"repetition_penalty": args.repetition_penalty},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    response = requests.post(base_url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    print(data["choices"][0]["message"]["content"])


if __name__ == "__main__":
    main()
