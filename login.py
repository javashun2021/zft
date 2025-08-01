from flask import Blueprint, request, jsonify

login_bp = Blueprint('login', __name__)

@login_bp.route('/login', methods=['GET'])
def login():
    # 获取请求头
    headers = dict(request.headers)

    # 获取请求体原始数据（文本格式）
    # body = request.get_data(as_text=True)

    # 构造保存内容
    # now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    content = ""
    for key, value in headers.items():
        content += f"{key}: {value}\n"

    # content += f"\n[Body]\n{body}\n\n"

    # 保存到本地文件
    with open("request_dump.txt", "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ 已保存请求内容到 request_dump.txt")

    return jsonify({'status': 'success', 'message': 'saved'})