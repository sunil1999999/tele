import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)

# =========================
# 🤖 COMMAND
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧮 Calculator Bot\n\nSend any math expression:\nExample:\n2+3*5"
    )

# =========================
# 🧮 CALCULATOR
# =========================
async def calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    expr = update.message.text

    try:
        # ⚠️ safe eval
        result = eval(expr, {"__builtins__": None}, {})
        await update.message.reply_text(f"✅ Result: {result}")
    except:
        await update.message.reply_text("❌ Invalid expression")

# =========================
# TELEGRAM APP
# =========================
application = Application.builder().token(TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, calculate))

# =========================
# WEBHOOK
# =========================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)

    import asyncio
    asyncio.run(application.process_update(update))

    return "ok"

@app.route("/")
def home():
    return "Calculator Bot Running ✅"

# =========================
# START
# =========================
if __name__ == "__main__":
    import asyncio

    async def main():
        await application.initialize()
        await application.start()
        await application.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")

    asyncio.run(main())

    port = int(os.environ.get("PORT", 10000))
    print("PORT:", port)

    app.run(host="0.0.0.0", port=port)
