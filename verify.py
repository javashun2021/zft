from flask import Blueprint, request, jsonify
import base64
import os
from PIL import Image
import io
import hashlib
import json
import requests
import traceback
import logging
logging.basicConfig(level=logging.INFO)

verify_bp = Blueprint('verify', __name__)
VERIFIED_FILE = "verified.json"
#OPENAI_API_KEY = "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"  # 请替换成你的 OpenAI API 密钥


API_KEY = "ctE1D8PGUklzBNsnA8ZA8xrp"
SECRET_KEY = "ksEDyTyte2gCuLW42uG0Lvp24pt6LDTt"

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

@verify_bp.route('/verify', methods=['POST'])
def verify_image():
    image_base64 = None

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON payload"}), 400

            # 1. image_path 方式
        if 'image_path' in data:
            image_path = data['image_path']
            if not os.path.exists(image_path):
                return jsonify({"error": "File path not found"}), 400
            with Image.open(image_path) as img:
                image_base64 = encode_image_to_base64(img)

        elif 'image_url' in data:
            image_url = data['image_url']
            resp = requests.get(image_url, timeout=10)
            if resp.status_code != 200:
                return jsonify({"error": f"Failed to fetch image from URL, status code: {resp.status_code}"}), 400
            img = Image.open(io.BytesIO(resp.content))
            image_base64 = encode_image_to_base64(img)

        elif 'image_base64' in data:
            raw_base64 = data['image_base64']
            # 如果是 data:image/png;base64,... 的形式，需要去掉前缀
            if ',' in raw_base64:
                raw_base64 = raw_base64.split(',')[1]
            image_base64 = raw_base64.strip().replace('\n', '')

        else:
            return jsonify({"error": "No valid image input provided"}), 400

        image_hash = get_image_hash(image_base64)
        # 在你的 verify_image 函数里
        logging.info("image_hash：%s", image_hash)
        if image_hash in verified_cache:
            return jsonify({"cached": True, "result": verified_cache[image_hash]})

        # 1. 读取图片并转换为base64
        #image_path = "test.png"  # 替换为你的验证码图片路径
        #with open(image_path, "rb") as f:
            #image_base64 = base64.b64encode(f.read()).decode('utf-8')

        # 2. 构造请求URL和参数
        url = "https://aip.baidubce.com/rest/2.0/ocr/v1/numbers?access_token=" + get_access_token()

        payload = {
            'image': image_base64,  # 关键参数：上传base64格式的图片
            'detect_direction': 'false'  # 是否检测图像朝向
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        # 3. 发送请求
        response = requests.post(url, headers=headers, data=payload)

        # 4. 输出结果
        data = response.json()

        # 在你的 verify_image 函数里
        logging.info("result：%s", json.dumps(data, ensure_ascii=False))
        result = data['words_result'][0]['words']


        verified_cache[image_hash] = result

        with open(VERIFIED_FILE, "w", encoding="utf-8") as f:
            json.dump(verified_cache, f, ensure_ascii=False, indent=2)

        return jsonify({"cached": False, "result": result})


    except Exception as e:
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc()  # 追加完整堆栈信息
        }), 500



def get_access_token():
    """获取百度OCR的access_token"""
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": API_KEY,
        "client_secret": SECRET_KEY
    }
    return str(requests.post(url, params=params).json().get("access_token"))
