import os
import json
import pymysql
from flask import Blueprint, request, jsonify
from datetime import datetime

query_bp = Blueprint('query', __name__)
QUERY_FILE = "queryed_orders.json"

db_config = {
    "host": "javashun2021.mysql.rds.aliyuncs.com",
    "port": 3306,
    "user": "root",
    "password": "Nizuibang521",
    "database": "third_payment",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

# 转换所有 datetime 类型为字符串
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
    if order_no in cache:
        return jsonify({"data": cache[order_no], "cached": True})

    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cursor:
            sql1 = """
                SELECT o.merchant_name, o.order_no, o.amount, o.user_id, o.client_ip, o.status, o.notify_status, o.create_time, ot.trace
                FROM `order` o
                LEFT JOIN order_trace ot ON o.order_no = ot.order_no
                WHERE o.platform_order_no = %s AND ot.trace LIKE 'buyerId:%%'
            """
            cursor.execute(sql1, (order_no,))
            result = cursor.fetchall()

            if not result:
                sql2 = """
                    SELECT o.merchant_name, o.order_no, o.amount, o.user_id, o.client_ip, o.status, o.notify_status, o.create_time
                    FROM `order` o WHERE platform_order_no = %s
                """
                cursor.execute(sql2, (order_no,))
                result = cursor.fetchall()

        conn.close()

        # 转换 datetime 为字符串
        converted_result = convert_datetime(result)

        # 写入缓存
        if result:
            cache[order_no] = converted_result
            save_cache(cache)

        return jsonify({"data": converted_result, "cached": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
