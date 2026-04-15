import os
import logging
import requests
import re
from bs4 import BeautifulSoup
from flask import Flask, request

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# =========================
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)
user_data = {}
HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# 🔍 SEARCH
def search_movie(name):
    url = f"https://bollyflix.frl/?s={name.replace(' ', '+')}"
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")
    return [(a.text.strip(), a.get("href")) for a in soup.select("h2 a")][:10]

# =========================
# 📥 EXTRACT LINKS
def extract_links(url):
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    data = []
    for h in soup.find_all(["h4", "h5"]):
        text = h.get_text(" ", strip=True)

        if not any(x in text.lower() for x in ["480","720","1080","4k"]):
            continue

        q = "4K" if "4k" in text.lower() else \
            "1080p" if "1080" in text else \
            "720p" if "720" in text else \
            "480p" if "480" in text else "Unknown"

        size_match = re.search(r'(\d+(?:\.\d+)?\s?(gb|mb))', text.lower())
        size = size_match.group(1) if size_match else "Unknown"

        p = h.find_next("p")
        if not p: continue

        a = p.find("a")
        if not a: continue

        data.append({
            "title": text,
            "quality": q,
            "size": size,
            "link": a.get("href")
        })

    return data

# =========================
def get_final_link(url):
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.find_all("a"):
        href = a.get("href")
        if href and "google" in href:
            return href
    return None

# =========================
# 🤖 HANDLERS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Send movie name")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    results = search_movie(text)
    user_data[user_id] = {"results": results}

    keyboard = [[InlineKeyboardButton(r[0], callback_data=f"m_{i}")]
                for i, r in enumerate(results)]

    await update.message.reply_text("🎬 Select Movie:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data.startswith("m_"):
        movie = user_data[user_id]["results"][int(data.split("_")[1])]
        links = extract_links(movie[1])
        user_data[user_id]["links"] = links

        keyboard = [[InlineKeyboardButton(f"{l['quality']} • {l['size']}", callback_data=f"q_{i}")]
                    for i, l in enumerate(links)]

        await query.edit_message_text("Select Quality:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("q_"):
        selected = user_data[user_id]["links"][int(data.split("_")[1])]
        final = get_final_link(selected["link"])

        if final:
            await query.message.reply_text(f"🔗 {final}")
        else:
            await query.message.reply_text("❌ Not found")

# =========================
# 🚀 TELEGRAM APP
application = Application.builder().token(TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
application.add_handler(CallbackQueryHandler(button))

# =========================
# 🌐 WEBHOOK ROUTE
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "Bot running ✅"

# =========================
# 🚀 START
if __name__ == "__main__":
    import asyncio

    async def main():
        await application.initialize()
        await application.start()
        await application.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")

    asyncio.run(main())

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
