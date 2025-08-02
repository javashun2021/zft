from flask import Flask
from login import login_bp
from convert import convert_bp
from refund import refund_bp
from query import query_bp
from querys import querys_bp
from verify import verify_bp

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 设置最大请求体为 50MB
app.register_blueprint(login_bp)
app.register_blueprint(convert_bp)
app.register_blueprint(refund_bp)
app.register_blueprint(query_bp)
app.register_blueprint(querys_bp)
app.register_blueprint(verify_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
