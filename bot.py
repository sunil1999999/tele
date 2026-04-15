import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)
user_data = {}

# =========================
# 🎨 BUTTON UI
# =========================
def keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("7️⃣", callback_data="7"), InlineKeyboardButton("8️⃣", callback_data="8"), InlineKeyboardButton("9️⃣", callback_data="9"), InlineKeyboardButton("➗", callback_data="/")],
        [InlineKeyboardButton("4️⃣", callback_data="4"), InlineKeyboardButton("5️⃣", callback_data="5"), InlineKeyboardButton("6️⃣", callback_data="6"), InlineKeyboardButton("✖️", callback_data="*")],
        [InlineKeyboardButton("1️⃣", callback_data="1"), InlineKeyboardButton("2️⃣", callback_data="2"), InlineKeyboardButton("3️⃣", callback_data="3"), InlineKeyboardButton("➖", callback_data="-")],
        [InlineKeyboardButton("0️⃣", callback_data="0"), InlineKeyboardButton(".", callback_data="."), InlineKeyboardButton("🟰", callback_data="="), InlineKeyboardButton("➕", callback_data="+")],
        [InlineKeyboardButton("🔙", callback_data="back"), InlineKeyboardButton("🧹", callback_data="C")]
    ])

def display(expr):
    return f"🧮 *Calculator*\n\n`{expr if expr else '0'}`"

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id] = ""
    await update.message.reply_text(display(""), reply_markup=keyboard(), parse_mode="Markdown")

# =========================
# BUTTON
# =========================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    expr = user_data.get(uid, "")
    data = query.data

    if data == "C":
        expr = ""
    elif data == "back":
        expr = expr[:-1]
    elif data == "=":
        try:
            expr = str(eval(expr))
        except:
            expr = "Error"
    else:
        expr += data

    user_data[uid] = expr

    await query.edit_message_text(display(expr), reply_markup=keyboard(), parse_mode="Markdown")

# =========================
# TELEGRAM APP
# =========================
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))

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
    return "Calculator Running ✅"

# =========================
# START (IMPORTANT FIX)
# =========================
if __name__ == "__main__":
    import asyncio

    async def setup():
        await application.initialize()
        await application.start()
        await application.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")

    asyncio.run(setup())

    port = int(os.environ.get("PORT", 10000))
    print("PORT:", port)

    # ✅ THIS LINE FIXES YOUR ERROR
    app.run(host="0.0.0.0", port=port)
