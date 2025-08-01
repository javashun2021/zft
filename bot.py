

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
import re


def handle_text(update, context):
    message = update.message.text.strip()

    if message.startswith("转单"):
        # 提取订单号（假设格式是 查询 + 空格 + 订单号）
        match = re.search(r'转单\s*([A-Z0-9]+)', message)
        if match:
            order_no = match.group(1)
            update.message.reply_text(f"✅ 收到转单订单号：{order_no}，正在处理...")

            try:
                url = f"http://8.217.186.177:5000/convert?orderNos={order_no}"
                response = requests.get(url)
                data = response.json()
                merchant_nos = [item["merchantTradeNo"] for item in data.get("results", [])]
                if merchant_nos:
                    result = ",".join(merchant_nos)
                    update.message.reply_text(f"📦 结果：\n{result}")
                else:
                    update.message.reply_text("❗ 没有找到任何结果")
            except Exception as e:
                update.message.reply_text(f"❌ 请求错误：{str(e)}")
        else:
            update.message.reply_text("⚠️ 格式错误，请发送格式如：查询 T3XXXXXX")
    else:
        # 忽略非查询指令
        pass

def main():
    updater = Updater("5849011897:AAEUpFVWwE4PKVJq1UXusNjiZL3IfhZmS8E", use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    #dp.add_handler(CommandHandler("convert", convert))  # 注册命令

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":  # 注意这里是 __name__
    main()
