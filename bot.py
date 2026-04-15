from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

TOKEN = os.getenv("BOT_TOKEN")  # safer for deployment

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! 🤖 Your bot is working on Render 🚀")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /start to check if I am alive!")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))

print("Bot running...")
app.run_polling()