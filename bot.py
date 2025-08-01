import logging
import requests
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# 日志配置
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = '5849011897:AAEUpFVWwE4PKVJq1UXusNjiZL3IfhZmS8E'
GROUP_CHAT_ID = -4961641914  # 群组 ID

# /convert 命令
def convert(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        update.message.reply_text("请提供订单号，例如：/convert 2025073198373")
        return

    order_nums = ",".join(args)
    try:
        response = requests.get(f"http://127.0.0.1:5000/convert?orderNos={order_nums}")
        result = response.json()
        update.message.reply_text(f"转化结果：\n{result}")
    except Exception as e:
        update.message.reply_text(f"转化失败：{str(e)}")

# /callback 命令
def callback(update: Update, context: CallbackContext):
    bot = context.bot
    bot.send_message(chat_id=GROUP_CHAT_ID, text="Hello 群组，这是我发的消息！")
    update.message.reply_text("你好，这是 /callback 指令")

# /start 命令
def start(update: Update, context: CallbackContext):
    update.message.reply_text("你好，这是 /start 指令")

# /help 命令
def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("你可以用 /start /help /callback /convert")

# /loginZft 命令
def loginZft(update: Update, context: CallbackContext):
    update.message.reply_text("登入中")

def main():
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("callback", callback))
    dp.add_handler(CommandHandler("convert", convert))
    dp.add_handler(CommandHandler("loginZft", loginZft))

    print("Bot 正在运行...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
