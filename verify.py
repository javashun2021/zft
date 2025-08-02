from flask import Blueprint, request, jsonify
import base64
import os
from PIL import Image
import io
import hashlib
import json
import requests

verify_bp = Blueprint('verify', __name__)
VERIFIED_FILE = "verified.json"
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"  # 请替换成你的 OpenAI API 密钥

# 加载缓存
if os.path.exists(VERIFIED_FILE):
    with open(VERIFIED_FILE, "r", encoding="utf-8") as f:
        verified_cache = json.load(f)
else:
    verified_cache = {}

def encode_image_to_base64(img: Image.Image) -> str:
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def get_image_hash(base64_str: str) -> str:
    return hashlib.sha1(base64_str.encode('utf-8')).hexdigest()

@verify_bp.route('/verify-image', methods=['POST'])
def verify_image():
    image_base64 = None

    try:
        # 1. 接收 image_path
        if 'image_path' in request.form:
            image_path = request.form['image_path']
            if not os.path.exists(image_path):
                return jsonify({"error": "File path not found"}), 400
            with Image.open(image_path) as img:
                image_base64 = encode_image_to_base64(img)

        # 2. 接收 image_file
        elif 'image_file' in request.files:
            file = request.files['image_file']
            img = Image.open(file.stream)
            image_base64 = encode_image_to_base64(img)

        # 3. 接收 base64 文本
        elif 'image_base64' in request.form:
            raw_base64 = request.form['image_base64']
            image_base64 = raw_base64.strip().replace('\n', '')

        else:
            return jsonify({"error": "No valid image input provided"}), 400

        image_hash = get_image_hash(image_base64)
        if image_hash in verified_cache:
            return jsonify({"cached": True, "result": verified_cache[image_hash]})

        # 使用 requests 调用 OpenAI API
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请识别并验证这张图片的内容"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        if response.status_code != 200:
            return jsonify({"error": "OpenAI API Error", "details": response.text}), 500

        result = response.json()['choices'][0]['message']['content']

        verified_cache[image_hash] = result
        with open(VERIFIED_FILE, "w", encoding="utf-8") as f:
            json.dump(verified_cache, f, ensure_ascii=False, indent=2)

        return jsonify({"cached": False, "result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
