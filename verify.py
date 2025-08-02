from flask import Blueprint, request, jsonify
import base64
import os
from PIL import Image
import io
import openai
import hashlib
import json

verify_bp = Blueprint('verify', __name__)
VERIFIED_FILE = "verified.json"  # 缓存文件路径
openai.api_key = "YOUR_OPENAI_API_KEY"  # 替换成你的 OpenAI Key

# 加载缓存
if os.path.exists(VERIFIED_FILE):
    with open(VERIFIED_FILE, "r", encoding="utf-8") as f:
        verified_cache = json.load(f)
else:
    verified_cache = {}

def encode_image_to_base64(img: Image.Image) -> str:
    """将图片对象转为 base64 字符串"""
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def get_image_hash(base64_str: str) -> str:
    """对图片的 base64 内容做 SHA1 哈希，作为唯一标识"""
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

        # 2. 接收 image_file 文件
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

        # 哈希检查是否已缓存
        image_hash = get_image_hash(image_base64)
        if image_hash in verified_cache:
            return jsonify({"cached": True, "result": verified_cache[image_hash]})

        # GPT-4 Vision 识别
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[
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
            max_tokens=1000
        )
        result = response.choices[0].message['content']

        # 存入缓存
        verified_cache[image_hash] = result
        with open(VERIFIED_FILE, "w", encoding="utf-8") as f:
            json.dump(verified_cache, f, ensure_ascii=False, indent=2)

        return jsonify({"cached": False, "result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
