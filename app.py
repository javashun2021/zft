from flask import Flask
from login import login_bp
from convert import convert_bp
from refund import refund_bp

app = Flask(__name__)
app.register_blueprint(login_bp)
app.register_blueprint(convert_bp)
app.register_blueprint(refund_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)