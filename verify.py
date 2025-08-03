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
#import pytesseract
import cv2
import numpy as np

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
def encode_image_to_base64_bytes(img: Image.Image) -> tuple[str, bytes]:
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    return image_base64, image_bytes

def get_image_hash(base64_str: str) -> str:
    return hashlib.sha1(base64_str.encode('utf-8')).hexdigest()

@verify_bp.route('/verify', methods=['POST'])
def verify_image():
    image_base64 = None
    image_bytes = None

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
                image_base64,image_bytes = encode_image_to_base64_bytes(img)

        elif 'image_url' in data:
            image_url = data['image_url']
            resp = requests.get(image_url, timeout=10)
            if resp.status_code != 200:
                return jsonify({"error": f"Failed to fetch image from URL, status code: {resp.status_code}"}), 400
            img = Image.open(io.BytesIO(resp.content))
            image_base64,image_bytes = encode_image_to_base64_bytes(img)

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

        #result = preprocess_image(image_bytes)
        preprocess_image(image_bytes)
        #if not result or not result.strip():
            #return jsonify({"error": "识别结果为空"}), 400

        # 1. 读取图片并转换为base64
        #image_path = "test.png"  # 替换为你的验证码图片路径
        #with open(image_path, "rb") as f:
            #image_base64 = base64.b64encode(f.read()).decode('utf-8')
        if not os.path.exists("output_images/step_7_opening.jpg"):
            return jsonify({"error": "output_images File path not found"}), 400
        with Image.open("output_images/step_7_opening.jpg") as img:
            image_base64 = encode_image_to_base64(img)

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

        if 'words_result' not in data or not data['words_result']:
            return jsonify({"error": "未识别出任何文字"}), 400

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

def recognize_captcha(image_bytes):
    url = 'http://upload.chaojiying.net/Upload/Processing.php'
    data = {
        'user': 'ned001',
        'pass2': 'pi774zgn',
        'softid': '972048',
        'codetype': '4004'  # 例：4位英数字
    }
    files = {'userfile': ('test.png', image_bytes)}
    response = requests.post(url, data=data, files=files)
    return response.json()

def preprocess_image(image_bytes):
    output_dir = "output_images"
    os.makedirs(output_dir, exist_ok=True)

    # ✅ 把字节流转成 numpy 数组
    img_array = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)  # ✅ 这里可以读字节流

    # 检查是否读取成功
    if img is None:
        raise ValueError("图片读取失败，可能不是有效图片格式")

    cv2.imwrite(os.path.join(output_dir, "step_1_original.jpg"), img)
    # 转灰度
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(os.path.join(output_dir, "step_2_gray.jpg"), gray)
    # 二值化（阈值可调）
    # _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    # 自动二值化
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(os.path.join(output_dir, "step_3_threshold.jpg"), thresh)
    # 去噪（形态学开运算）
    # kernel = np.ones((2, 2), np.uint8)
    # opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    opening = cv2.medianBlur(thresh, 3)
    cv2.imwrite(os.path.join(output_dir, "step_4_opening.jpg"), opening)

    # 如果是黑底白字，反转颜色
    vert = cv2.bitwise_not(opening)
    cv2.imwrite(os.path.join(output_dir, "step_5_opening.jpg"), vert)

    # 转成 RGB 供 Tesseract 使用
    rgb_img = cv2.cvtColor(vert, cv2.COLOR_GRAY2RGB)
    cv2.imwrite(os.path.join(output_dir, "step_6_opening.jpg"), rgb_img)

    # 放大
    bigger = cv2.resize(rgb_img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(os.path.join(output_dir, "step_7_opening.jpg"), bigger)

    # OCR 识别（只识别数字）
    #code = pytesseract.image_to_string(bigger, config='--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789 -c classify_bln_numeric_mode=1')

    #return code
