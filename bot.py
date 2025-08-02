from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
import re


def handle_text(update, context):
    message = update.message.text.strip()
    # 第一步：将中文逗号替换成英文逗号
    # message = message.replace('，', ',')
    # 检查是否含有换行符，用于决定返回格式
    #needRow = '\n' in message

    #message = message.replace('，', ',').replace(' ', ',').replace('\n', ',')
    #message = re.sub(r',+', ',', message).strip(',')  # 合并多余逗号，去首尾逗号
    if message.startswith("转单"):
        # 去掉前缀“转单”，然后保留换行结构
        message_body = message[len("转单"):].strip()

        # 把每一行提取出来（保留行结构）
        lines = [line.strip() for line in message_body.splitlines() if line.strip()]

        all_results = []

        for line in lines:
            # 替换中文逗号为英文逗号，清理多余空格
            clean_line = re.sub(r',+', ',', line.replace('，', ',').replace(' ', ',')).strip(',')

            if not re.match(r'^[A-Z0-9,]+$', clean_line):
                update.message.reply_text("⚠️ 检测到非法字符，请确认订单号格式正确")
                return

            try:
                url = f"http://127.0.0.1:5000/convert?orderNos={clean_line}"
                response = requests.get(url, timeout=10)
                data = response.json()
                merchant_nos = [item["merchantTradeNo"] for item in data.get("results", [])]

                if merchant_nos:
                    result_line = ",".join(merchant_nos)
                else:
                    result_line = "❗该行未查到结果"

                all_results.append(result_line)
            except Exception as e:
                update.message.reply_text(f"❌ 请求错误：{str(e)}")
                return

        final_reply = "\n".join(all_results)
        update.message.reply_text(f"📦 结果：\n{final_reply}")
    elif message.startswith("退款"):
        # 提取订单号（假设格式是 查询 + 空格 + 订单号）
        message = message.replace('，', ',').replace(' ', ',').replace('\n', ',')
        message = re.sub(r',+', ',', message).strip(',')  # 合并多余逗号，去首尾逗号

        match = re.search(r'退款\s*([A-Z0-9,]+)', message)
        if match:
            order_nos = match.group(1)
            update.message.reply_text(f"✅ 收到退款订单号：{order_nos}，正在处理...")

            try:
                url = f"http://127.0.0.1:5000/refund?type=1&orderNos={order_nos}"
                response = requests.get(url)
                data = response.json()
                # 提取 msg 信息
                results = data.get("results", [])
                if results:
                    messages = []
                    for item in results:
                        msg = item.get("response", {}).get("msg", "未知错误")
                        messages.append(f"{item.get('orderNo', '未知订单')}：{msg}")
                    final_message = "\n".join(messages)
                    update.message.reply_text(f"📦 结果：\n{final_message}")
                else:
                    update.message.reply_text("❗ 没有查询到结果")
            except Exception as e:
                update.message.reply_text(f"❌ 请求错误：{str(e)}")
        else:
            update.message.reply_text("⚠️ 格式错误，请发送格式如：退款 T3XXXXXX")
    elif message.startswith("查单"):
        # 提取订单号（假设格式是 查询 + 空格 + 订单号）
        message = message.replace('，', ',').replace(' ', ',').replace('\n', ',')
        message = re.sub(r',+', ',', message).strip(',')  # 合并多余逗号，去首尾逗号
        # 提取订单号列表
        match = re.search(r'查单\s*([A-Z0-9,]+)', message)
        if match:
            order_nos_raw = match.group(1)
            order_nos = [no.strip() for no in order_nos_raw.split(',') if no.strip()]
            update.message.reply_text(f"✅ 收到查询订单号：{', '.join(order_nos)}，正在处理...")

            messages = []

            for order_no in order_nos:
                try:
                    url = f"http://127.0.0.1:5000/query?orderNo={order_no}"
                    response = requests.get(url, timeout=10)
                    data = response.json()

                    results = data.get("data", [])
                    if not results:
                        messages.append(f"🔍 订单号 {order_no}：未查询到结果")
                        continue

                    for item in results:
                        merchant_name = item.get("merchant_name", "未知商户")
                        amount = item.get("amount", "未知金额")
                        status = item.get("status", "")
                        notify_status = item.get("notify_status", "")
                        create_time = item.get("create_time", "未知时间")

                        pay_status = "✅ 已支付" if status == "Paid" else "❌ 未支付"
                        notify_state = "✅ 已回调" if notify_status == "Notify_Success" else "❌ 未回调"

                        block_info = item.get("block_info", {})
                        buyer_id = block_info.get("buyer_id", "未知")
                        is_blocked = item.get("is_blocked", False)
                        block_text = "🧱 是砖头" if is_blocked else "❓ 未知"

                        remark = ""
                        if status == "Paid" and notify_status != "Notify_Success" and not is_blocked:
                            remark = "💡 备注：单日限制"

                        msg = (
                            f"📌 订单号：{order_no}\n"
                            f"📌 商户：{merchant_name}\n"
                            f"💰 金额：{amount}\n"
                            f"📥 支付状态：{pay_status}\n"
                            f"📬 回调状态：{notify_state}\n"
                            f"🆔 支付宝ID：{buyer_id}\n"
                            f"🔍 是否为砖头：{block_text}\n"
                            f"🕒 创建时间：{create_time}"
                        )
                        if remark:
                            msg += f"\n{remark}"

                        messages.append(msg)

                except Exception as e:
                    messages.append(f"❌ 查询订单号 {order_no} 失败：{str(e)}")

            # 合并并返回所有结果
            final_message = "\n\n".join(messages)
            update.message.reply_text(f"📦 查询结果：\n\n{final_message}")

        else:
            update.message.reply_text("⚠️ 格式错误，请发送格式如：查单 T3XXXXXX 或多个订单号用逗号分隔")
    else:
        # 忽略非查询指令
        pass


def main():
    updater = Updater("5849011897:AAEUpFVWwE4PKVJq1UXusNjiZL3IfhZmS8E", use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    # dp.add_handler(CommandHandler("convert", convert))  # 注册命令

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":  # 注意这里是 __name__
    main()
