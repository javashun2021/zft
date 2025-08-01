from telegram.ext import Updater, CommandHandler
import requests

def convert(update, context):
    update.message.reply_text("✅ 收到指令，正在查询...")

    try:
        # 获取指令参数
        if len(context.args) == 0:
            update.message.reply_text("⚠️ 请提供订单号，例如 /convert T3AWZ03382025073020260239137")
            return
        order_no = context.args[0]

        # 构造请求 URL
        url = f"http://8.217.186.177:5000/convert?orderNos={order_no}"
        resp = requests.get(url, timeout=10)

        # 检查响应状态码
        if resp.status_code == 200:
            update.message.reply_text(f"✅ 查询成功：\n{resp.text}")
        else:
            update.message.reply_text(f"❌ 查询失败，状态码：{resp.status_code}")
    except Exception as e:
        update.message.reply_text(f"❌ 请求出错：{str(e)}")

    except Exception as e:
        # 出错时返回错误信息
        update.message.reply_text(f"❌ 处理出错：{str(e)}")


def main():
    updater = Updater("5849011897:AAEUpFVWwE4PKVJq1UXusNjiZL3IfhZmS8E", use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("convert", convert))  # 注册命令

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":  # 注意这里是 __name__
    main()
