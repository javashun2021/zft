import json
import os
from flask import Blueprint, request
import requests
from datetime import datetime, timedelta
import calendar

refund_bp = Blueprint('refund', __name__)

REFUNDED_FILE = "refunded_orders.json"  # 缓存已退款订单信息


def read_headers():
    with open("request_dump.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    headers = {}
    for line in lines:
        if ": " in line:
            key, value = line.strip().split(": ", 1)
            headers[key] = value
    return headers


def get_month_range(offset):
    today = datetime.today().replace(day=1)
    target = today - timedelta(days=offset * 30)
    begin = target.replace(day=1)
    end_day = calendar.monthrange(target.year, target.month)[1]
    end = target.replace(day=end_day)
    return begin.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def load_refunded_orders():
    if os.path.exists(REFUNDED_FILE):
        with open(REFUNDED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_refunded_orders(data):
    with open(REFUNDED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@refund_bp.route('/refund', methods=['GET'])
def refund():
    headers = read_headers()
    order_nos_param = request.args.get("orderNos")
    query_type = int(request.args.get("type", 0))  # 0 = platformOutTradeNo，1 = merchantTradeNo
    query_key = "platformOutTradeNo" if query_type == 0 else "merchantTradeNo"

    if not order_nos_param:
        return {"error": "Missing orderNos"}, 400

    order_nos = order_nos_param.split(",")
    refunded_cache = load_refunded_orders()
    results = []

    for order_no in order_nos:
        if order_no in refunded_cache:
            results.append({
                "orderNo": order_no,
                "cached": True,
                "result": refunded_cache[order_no]
            })
            continue

        refund_success = False
        for i in range(6):
            begin, end = get_month_range(i)
            url = f"https://home.zhilianzhifu.com/api/v1/merchant-order?pageIndex=1&pageSize=10&{query_key}={order_no}&statisticType=1&beginTime={begin}&endTime={end}"
            r = requests.get(url, headers=headers)

            if r.status_code == 200:
                data = r.json().get("data", {})
                lst = data.get("list", [])
                if data.get("count", 0) > 0 and lst:
                    obj = lst[0]
                    order_id = obj["id"]
                    refund_url = f"https://home.zhilianzhifu.com/api/v1/merchant-order/refund/{order_id}/{begin}"
                    put_res = requests.put(refund_url, headers=headers)
                    res_data = {
                        "orderNo": order_no,
                        "refund_url": refund_url,
                        "status": put_res.status_code,
                        "response": put_res.json() if put_res.headers.get("Content-Type", "").startswith("application/json") else put_res.text
                    }
                    results.append(res_data)
                    refunded_cache[order_no] = res_data
                    refund_success = True
                    break

        if not refund_success:
            fail_data = {"orderNo": order_no, "error": "No order found in last 6 months"}
            results.append(fail_data)

    save_refunded_orders(refunded_cache)
    return {"results": results}
