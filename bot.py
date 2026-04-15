import os
import logging
import requests
import re
import threading
import asyncio
from bs4 import BeautifulSoup
from flask import Flask, request

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# =========================
# 🔥 LOGGING
# =========================
logging.basicConfig(level=logging.INFO)

# =========================
# 🌐 FLASK SERVER
# =========================
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "Bot is running ✅"

# =========================
# 🔑 TOKEN
# =========================
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN not found")

HEADERS = {"User-Agent": "Mozilla/5.0"}
user_data = {}

# =========================
# 🔍 SEARCH
# =========================
def search_movie(name):
    url = f"https://bollyflix.frl/?s={name.replace(' ', '+')}"
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")
    return [(a.text.strip(), a.get("href")) for a in soup.select("h2 a")][:10]

# =========================
# 📥 EXTRACT LINKS
# =========================
def extract_links(url):
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    data = []

    for h in soup.find_all(["h4", "h5"]):
        text = h.get_text(" ", strip=True)

        if not any(x in text.lower() for x in ["480", "720", "1080", "4k"]):
            continue

        if "4k" in text.lower():
            q = "4K"
        elif "1080" in text:
            q = "1080p"
        elif "720" in text:
            q = "720p"
        elif "480" in text:
            q = "480p"
        else:
            q = "Unknown"

        size_match = re.search(r'(\d+(?:\.\d+)?\s?(gb|mb))', text.lower())
        size = size_match.group(1) if size_match else "Unknown"

        p = h.find_next("p")
        if not p:
            continue

        a = p.find("a")
        if not a:
            continue

        href = a.get("href")

        if href:
            data.append({
                "title": text,
                "quality": q,
                "size": size,
                "link": href
            })

    return data

# =========================
# 🔥 FINAL LINK
# =========================
def get_final_link(url):
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.find_all("a"):
        href = a.get("href")
        if href and ("drive.google" in href or "google" in href):
            return href

    return None

# =========================
# 🤖 COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Send movie name")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is working!")

# =========================
# 🎬 SEARCH HANDLER
# =========================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    results = search_movie(text)
    user_data[user_id] = {"results": results}

    keyboard = [[InlineKeyboardButton(r[0], callback_data=f"m_{i}")]
                for i, r in enumerate(results)]

    await update.message.reply_text("🎬 Select Movie:", reply_markup=InlineKeyboardMarkup(keyboard))

# =========================
# 🔘 BUTTON HANDLER
# =========================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data.startswith("m_"):
        movie = user_data[user_id]["results"][int(data.split("_")[1])]

        links = extract_links(movie[1])
        user_data[user_id]["links"] = links

        keyboard = [[InlineKeyboardButton(
            f"🎞 {l['quality']} • 📦 {l['size']}",
            callback_data=f"q_{i}"
        )] for i, l in enumerate(links)]

        await query.edit_message_text("📥 Select Quality:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("q_"):
        selected = user_data[user_id]["links"][int(data.split("_")[1])]

        await query.edit_message_text(
            f"🎬 {selected['title']}\n"
            f"━━━━━━━━━━━━\n"
            f"🎞 {selected['quality']}\n"
            f"📦 {selected['size']}"
        )

        final = get_final_link(selected["link"])

        if final:
            await query.message.reply_text(f"🔗 Download Link:\n{final}")
        else:
            await query.message.reply_text("❌ Link not found")

# =========================
# 🌐 WEBHOOK ROUTE (FIXED)
# =========================
@app_web.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)

    # ✅ DIRECT PROCESS (IMPORTANT FIX)
    asyncio.run(bot_app.process_update(update))

    return "ok"

# =========================
# 🚀 START BOT FUNCTION
# =========================
def start_bot():
    async def main():
        global bot_app

        bot_app = ApplicationBuilder().token(TOKEN).build()

        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("test", test))
        bot_app.add_handler(MessageHandler(filters.TEXT, handle))
        bot_app.add_handler(CallbackQueryHandler(button))

        await bot_app.initialize()
        await bot_app.start()

        WEBHOOK_URL = os.getenv("WEBHOOK_URL")
        print("WEBHOOK:", WEBHOOK_URL)

        await bot_app.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")

    asyncio.run(main())

# =========================
# 🚀 MAIN START
# =========================
if __name__ == "__main__":

    # start bot in background
    threading.Thread(target=start_bot).start()

    # start flask
    port = int(os.environ.get("PORT", 10000))
    print("PORT:", port)

    app_web.run(host="0.0.0.0", port=port)
