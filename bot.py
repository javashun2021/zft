from telegram import Update
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import time
from io import BytesIO

TOKEN = '5849011897:AAEUpFVWwE4PKVJq1UXusNjiZL3IfhZmS8E'
GROUP_CHAT_ID = -4961641914  # 你的群组ID

# 定义一个带参数的命令
async def query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args  # 获取参数列表
    if not args:
        await update.message.reply_text("请提供一个订单号，例如：/query 2025073198373")
        return

    orderNum = " ".join(args)
    await update.message.reply_text(f"你的订单查询结果是：{orderNum}")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=GROUP_CHAT_ID, text="Hello 群组，这是我发的消息！")
    await update.message.reply_text("你好，这是 /callback 指令")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("你好，这是 /start 指令")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("你可以用 /start  /help /callback  /query")

async def loginZft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("登入中")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("query",query))
    app.add_handler(CommandHandler("callback", callback))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("loginZft",loginZft))
    app.add_handler(CommandHandler("help", help_command))

    print("Bot 正在运行...")
    app.run_polling()
