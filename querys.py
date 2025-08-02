import os
import json
import pymysql
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta

querys_bp = Blueprint('querys', __name__)
QUERY_FILE = "queryed_orders.json"
CACHE_EXPIRE_SECONDS = 3600  # 缓存有效时间，单位秒

db_config = {
    "host": "javashun2021.mysql.rds.aliyuncs.com",
    "port": 3306,
    "user": "root",
    "password": "Nizuibang521",
    "database": "third_payment",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

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

@querys_bp.route('/querys', methods=['GET'])
def query_multiple_orders():
    order_nos_str = request.args.get('orderNos')
    if not order_nos_str:
        return jsonify({"error": "缺少参数：orderNos"}), 400

    order_nos = [o.strip() for o in order_nos_str.split(',') if o.strip()]
    if not order_nos:
        return jsonify({"error": "参数 orderNos 无有效内容"}), 400

    cache = load_cache()
    now = datetime.now()
    results = []

    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cursor:
            for order_no in order_nos:
                cached_item = cache.get(order_no)
                cached_time = None
                if cached_item:
                    try:
                        cached_time = datetime.strptime(cached_item.get("timestamp", ""), "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass

                if cached_item and cached_time and now - cached_time < timedelta(seconds=CACHE_EXPIRE_SECONDS):
                    data_item = cached_item["data"]
                    if isinstance(data_item, list):
                        for entry in data_item:
                            entry["cached"] = True
                            entry["order_query_no"] = order_no
                            results.append(entry)
                    continue  # 跳过查询

                # 第一次查询，带 trace
                sql1 = """
                    SELECT o.merchant_name, o.order_no, o.amount, o.user_id, o.client_ip, o.status, o.notify_status, o.create_time, ot.trace
                    FROM `order` o
                    LEFT JOIN order_trace ot ON o.order_no = ot.order_no
                    WHERE o.platform_order_no = %s AND ot.trace LIKE 'buyerId:%%'
                """
                cursor.execute(sql1, (order_no,))
                result = cursor.fetchall()

                if result:
                    trace = result[0].get("trace", "")
                    if trace.startswith("buyerId:"):
                        buyer_id = trace.replace("buyerId:", "")
                        sql3 = "SELECT buyer_id,client_ip,user_id,create_time,content FROM `order_block` WHERE buyer_id = %s"
                        cursor.execute(sql3, (buyer_id,))
                        block_result = cursor.fetchone()
                        if block_result:
                            result[0]["is_blocked"] = True
                            result[0]["block_info"] = convert_datetime(block_result)
                        else:
                            result[0]["is_blocked"] = False
                    else:
                        result[0]["is_blocked"] = False
                else:
                    # fallback 查询
                    sql2 = """
                        SELECT o.merchant_name, o.order_no, o.amount, o.user_id, o.client_ip, o.status, o.notify_status, o.create_time
                        FROM `order` o WHERE platform_order_no = %s
                    """
                    cursor.execute(sql2, (order_no,))
                    result = cursor.fetchall()

                    if result:
                        result[0]["is_blocked"] = False

                # 加入当前查询订单号标记
                for item in result:
                    item["cached"] = False
                    item["order_query_no"] = order_no
                    results.append(item)

                # 写入缓存（结构统一）
                cache[order_no] = {
                    "data": convert_datetime(result),
                    "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
                }

        conn.close()
        save_cache(cache)

        return jsonify({"results": convert_datetime(results)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
