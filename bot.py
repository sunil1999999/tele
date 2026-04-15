import os
import logging
import requests
import re
from bs4 import BeautifulSoup
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)
user_data = {}

# =========================
# SEARCH
def search_movie(name):
    url = f"https://bollyflix.frl/?s={name.replace(' ', '+')}"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    return [(a.text.strip(), a.get("href")) for a in soup.select("h2 a")][:10]

# =========================
# COMMAND
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Send movie name")

# =========================
# MESSAGE
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = search_movie(update.message.text)

    if not results:
        await update.message.reply_text("❌ Not found")
        return

    keyboard = [[InlineKeyboardButton(r[0], callback_data=str(i))]
                for i, r in enumerate(results)]

    context.user_data["results"] = results

    await update.message.reply_text("Select movie:", reply_markup=InlineKeyboardMarkup(keyboard))

# =========================
# BUTTON
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    results = context.user_data.get("results", [])
    index = int(query.data)

    await query.message.reply_text(f"Link:\n{results[index][1]}")

# =========================
# TELEGRAM APP
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
application.add_handler(CallbackQueryHandler(button))

# =========================
# WEBHOOK
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)

    import asyncio
    asyncio.run(application.process_update(update))

    return "ok"

@app.route("/")
def home():
    return "Bot running ✅"

# =========================
# START
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
