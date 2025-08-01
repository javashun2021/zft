import json
import os
from flask import Blueprint, request
import requests
from datetime import datetime, timedelta
import calendar

convert_bp = Blueprint('convert', __name__)

CACHE_FILE = "convert_cache.json"

def read_headers():
    with open("request_dump.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    headers = {}
    for line in lines:
        if ": " in line:
            key, value = line.strip().split(": ", 1)
            headers[key] = value
    return headers

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_month_range(offset):
    today = datetime.today().replace(day=1)
    target = today - timedelta(days=offset * 30)
    begin = target.replace(day=1)
    end_day = calendar.monthrange(target.year, target.month)[1]
    end = target.replace(day=end_day)
    return begin.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

@convert_bp.route('/convert', methods=['GET'])
def convert():
    order_nos = request.args.get("orderNos")
    if not order_nos:
        return {"error": "Missing orderNos"}, 400

    order_list = order_nos.split(",")
    headers = read_headers()
    result = []
    cache = load_cache()

    for order_no in order_list:
        if order_no in cache:
            result.append(cache[order_no])
            continue

        found = False
        for i in range(6):
            begin, end = get_month_range(i)
            url = f"https://home.zhilianzhifu.com/api/v1/merchant-order?pageIndex=1&pageSize=10&platformOutTradeNo={order_no}&statisticType=1&beginTime={begin}&endTime={end}"
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                data = r.json().get("data", {})
                lst = data.get("list", [])
                if data.get("count", 0) > 0 and lst:
                    obj = lst[0]
                    item = {
                        "merchantTradeNo": obj["merchantTradeNo"],
                        "totalAmount": obj["totalAmount"],
                        "buyerId": obj["buyerId"]
                    }
                    cache[order_no] = item
                    result.append(item)
                    found = True
                    break
        if not found:
            result.append({"orderNo": order_no, "error": "Not found in last 6 months"})

    save_cache(cache)
    return {"results": result}