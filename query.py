import os
import json
import pymysql
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from DBUtils.PooledDB import PooledDB  # ✅ 引入连接池

query_bp = Blueprint('query', __name__)
QUERY_FILE = "queryed_orders.json"

CACHE_EXPIRE_SECONDS = 3600

# ✅ 数据库配置
db_config = {
    "host": "javashun2021.mysql.rds.aliyuncs.com",
    "port": 3306,
    "user": "root",
    "password": "Nizuibang521",
    "database": "third_payment",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

# ✅ 创建连接池（只需初始化一次）
pool = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=2,
    blocking=True,
    **db_config
)

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
    with open(QUERY_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

@query_bp.route('/query', methods=['GET'])
def refund():
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

    try:
        conn = pool.connection()  # ✅ 从连接池中获取连接
        with conn.cursor() as cursor:
            sql1 = """
                SELECT o.merchant_name, o.order_no, o.amount, o.user_id, o.client_ip, o.status, o.notify_status, o.create_time, ot.trace
                FROM `order` o
                LEFT JOIN order_trace ot ON o.order_no = ot.order_no
                WHERE o.platform_order_no = %s AND ot.trace LIKE 'buyerId:%%'
            """
            cursor.execute(sql1, (order_no,))
            result = cursor.fetchall()

            block_info = None

            if result:
                trace = result[0].get("trace", "")
                if trace.startswith("buyerId:"):
                    buyer_id = trace.replace("buyerId:", "")
                    sql3 = "SELECT buyer_id,client_ip,user_id,create_time,content FROM `order_block` WHERE buyer_id = %s"
                    cursor.execute(sql3, (buyer_id,))
                    block_result = cursor.fetchone()
                    if block_result:
                        block_info = convert_datetime(block_result)
                        result[0]["is_blocked"] = True
                        result[0]["block_info"] = block_info
                    else:
                        result[0]["is_blocked"] = False
                else:
                    result[0]["is_blocked"] = False
            else:
                sql2 = """
                    SELECT o.merchant_name, o.order_no, o.amount, o.user_id, o.client_ip, o.status, o.notify_status, o.create_time
                    FROM `order` o WHERE platform_order_no = %s
                """
                cursor.execute(sql2, (order_no,))
                result = cursor.fetchall()

        conn.close()  # ✅ 归还连接到连接池

        if result:
            converted_result = convert_datetime(result)
            cache[order_no] = {
                "data": converted_result,
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
            }
            save_cache(cache)

        return jsonify({"data": converted_result, "cached": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
