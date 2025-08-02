import os
import json
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from filelock import FileLock  # ✅ 文件锁，防止并发写入问题
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

query_bp = Blueprint('query', __name__)
QUERY_FILE = "queryed_orders.json"
CACHE_EXPIRE_SECONDS = 3600

# ✅ 数据库配置
DB_URI = "mysql+pymysql://root:Nizuibang521@javashun2021.mysql.rds.aliyuncs.com:3306/third_payment?charset=utf8mb4"
engine = create_engine(DB_URI, pool_pre_ping=True)
Session = sessionmaker(bind=engine)

def convert_datetime(obj):
    if isinstance(obj, list):
        return [convert_datetime(item) for item in obj]
    if isinstance(obj, dict):
        return {k: (v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v) for k, v in obj.items()}
    return obj

def load_cache():
    if not os.path.exists(QUERY_FILE):
        return {}
    with open(QUERY_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_cache(cache):
    with FileLock(QUERY_FILE + ".lock"):
        with open(QUERY_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

@query_bp.route('/query', methods=['GET'])
def query_order():
    order_no = request.args.get('orderNo')
    if not order_no:
        return jsonify({"error": "缺少参数：orderNo"}), 400

    cache = load_cache()
    now = datetime.now()

    if order_no in cache:
        cached_item = cache[order_no]
        cached_time = datetime.strptime(cached_item.get("timestamp", "1970-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
        if now - cached_time < timedelta(seconds=CACHE_EXPIRE_SECONDS):
            return jsonify({"data": cached_item["data"], "cached": True})

    session = Session()
    try:
        sql1 = text("""
            SELECT o.merchant_name, o.order_no, o.amount, o.user_id, o.client_ip, o.status, o.notify_status, o.create_time, ot.trace
            FROM `order` o
            LEFT JOIN order_trace ot ON o.order_no = ot.order_no
            WHERE o.platform_order_no = :order_no AND ot.trace LIKE 'buyerId:%'
        """)
        result = session.execute(sql1, {"order_no": order_no}).mappings().all()

        if result:
            row = dict(result[0])
            trace = row.get("trace", "")
            if trace.startswith("buyerId:"):
                buyer_id = trace.replace("buyerId:", "")
                sql3 = text("""
                    SELECT buyer_id, client_ip, user_id, create_time, content
                    FROM `order_block`
                    WHERE buyer_id = :buyer_id
                """)
                block_result = session.execute(sql3, {"buyer_id": buyer_id}).mappings().first()
                if block_result:
                    row["is_blocked"] = True
                    row["block_info"] = convert_datetime(dict(block_result))
                else:
                    row["is_blocked"] = False
                    row["block_info"] = {}
            else:
                row["is_blocked"] = False
                row["block_info"] = {}
            result_data = [row]
        else:
            sql2 = text("""
                SELECT o.merchant_name, o.order_no, o.amount, o.user_id, o.client_ip, o.status, o.notify_status, o.create_time
                FROM `order` o
                WHERE platform_order_no = :order_no
            """)
            result = session.execute(sql2, {"order_no": order_no}).mappings().all()
            if result:
                row = dict(result[0])
                row["is_blocked"] = False
                row["block_info"] = {}
                result_data = [row]
            else:
                result_data = []

        converted_result = convert_datetime(result_data)
        cache[order_no] = {
            "data": converted_result,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
        }
        save_cache(cache)

        return jsonify({"data": converted_result, "cached": False})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        session.close()
