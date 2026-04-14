import requests
import re
from bs4 import BeautifulSoup

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8112140789:AAFs2PiS3b0rfNfVwkBnDth3ikrN2Uacq48"

user_data = {}
HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# 🔍 SEARCH
# =========================
def search_movie(name):
    url = f"https://bollyflix.frl/?s={name.replace(' ', '+')}"
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    return [(a.text.strip(), a.get("href")) for a in soup.select("h2 a")][:10]

# =========================
# 📥 EXTRACT (TITLE + QUALITY + SIZE)
# =========================
def extract_links(url):
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    data = []

    for h in soup.find_all(["h4", "h5"]):
        text = h.get_text(" ", strip=True)

        if not any(x in text.lower() for x in ["480", "720", "1080", "4k"]):
            continue

        # 🎬 FULL TITLE
        title = text

        # 🎞 QUALITY
        if "4k" in text.lower():
            quality = "4K"
        elif "1080" in text:
            quality = "1080p"
        elif "720" in text:
            quality = "720p"
        elif "480" in text:
            quality = "480p"
        else:
            quality = "Unknown"

        # 📦 SIZE
        size_match = re.search(r'(\d+(?:\.\d+)?\s?(gb|mb))', text.lower())
        size = size_match.group(1) if size_match else "Unknown"

        # 🔗 LINK
        p = h.find_next("p")
        if not p:
            continue

        a = p.find("a")
        if not a:
            continue

        href = a.get("href")

        if href:
            data.append({
                "title": title,
                "quality": quality,
                "size": size,
                "link": href
            })

    # remove duplicates
    seen = set()
    unique = []
    for d in data:
        key = (d["quality"], d["size"])
        if key not in seen:
            seen.add(key)
            unique.append(d)

    return unique

# =========================
# 📺 EXTRACT EPISODES
# =========================
def extract_episodes(url):
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    eps = []

    for a in soup.find_all("a"):
        href = a.get("href")
        text = a.get_text(strip=True)

        if href and any(x in text.lower() for x in ["episode", "ep"]):
            eps.append((text, href))

    # remove duplicates
    seen = set()
    unique = []
    for e in eps:
        if e[1] not in seen:
            seen.add(e[1])
            unique.append(e)

    return unique

# =========================
# 🔥 FINAL LINK
# =========================
def get_final_link(url):
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.find_all("a"):
        href = a.get("href")
        txt = a.text.lower()

        if href and any(x in txt for x in ["download", "click", "instant"]):
            return href

    for a in soup.find_all("a"):
        href = a.get("href")
        if href and ("drive" in href or "google" in href):
            return href

    return None

# =========================
# 🤖 START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Send movie / series name")

# =========================
# 🎬 SEARCH
# =========================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    results = search_movie(text)
    user_data[user_id] = {"results": results}

    keyboard = [
        [InlineKeyboardButton(r[0], callback_data=f"m_{i}")]
        for i, r in enumerate(results)
    ]

    await update.message.reply_text(
        "🎬 Select Movie:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# 🔘 BUTTON HANDLER
# =========================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # 🎬 MOVIE
    if data.startswith("m_"):
        movie = user_data[user_id]["results"][int(data.split("_")[1])]

        links = extract_links(movie[1])
        user_data[user_id]["links"] = links

        keyboard = [
            [InlineKeyboardButton(l["title"], callback_data=f"q_{i}")]
            for i, l in enumerate(links)
        ]

        await query.edit_message_text(
            "📥 Select Quality:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # 📥 QUALITY
    elif data.startswith("q_"):
        selected = user_data[user_id]["links"][int(data.split("_")[1])]
        link = selected["link"]

        # 📺 SERIES
        if "fxlinks" in link:
            eps = extract_episodes(link)

            if len(eps) > 1:
                user_data[user_id]["eps"] = eps

                keyboard = [
                    [InlineKeyboardButton(e[0], callback_data=f"ep_{i}")]
                    for i, e in enumerate(eps)
                ]

                await query.edit_message_text(
                    "📺 Select Episode:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return

        user_data[user_id]["link"] = link

        keyboard = [
            [InlineKeyboardButton("⚡ Instant", callback_data="inst")],
            [InlineKeyboardButton("📲 Telegram", callback_data="tele")]
        ]

        await query.edit_message_text(
            f"🎬 {selected['title']}\n\n"
            f"🎞 Quality: {selected['quality']}\n"
            f"📦 Size: {selected['size']}\n\n"
            "Choose method:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # 📺 EPISODE (KEEP LIST)
    elif data.startswith("ep_"):
        ep = user_data[user_id]["eps"][int(data.split("_")[1])]

        await query.message.reply_text(f"📺 {ep[0]}")

        user_data[user_id]["link"] = ep[1]

        keyboard = [
            [InlineKeyboardButton("⚡ Instant", callback_data="inst")],
            [InlineKeyboardButton("📲 Telegram", callback_data="tele")]
        ]

        await query.message.reply_text(
            "Choose method:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ⚡ FINAL
    elif data in ["inst", "tele"]:
        link = user_data[user_id]["link"]

        await query.message.reply_text("⏳ Processing...")

        final = get_final_link(link)

        if final:
            await query.message.reply_text(f"🔗 {final}")
        else:
            await query.message.reply_text("❌ Failed")

# =========================
# 🚀 RUN
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))
app.add_handler(CallbackQueryHandler(button))

print("🚀 BOT RUNNING...")
app.run_polling()