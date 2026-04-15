import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)
user_data = {}

# =========================
# UI
# =========================
def keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("7️⃣","7"), InlineKeyboardButton("8️⃣","8"), InlineKeyboardButton("9️⃣","9"), InlineKeyboardButton("➗","/")],
        [InlineKeyboardButton("4️⃣","4"), InlineKeyboardButton("5️⃣","5"), InlineKeyboardButton("6️⃣","6"), InlineKeyboardButton("✖️","*")],
        [InlineKeyboardButton("1️⃣","1"), InlineKeyboardButton("2️⃣","2"), InlineKeyboardButton("3️⃣","3"), InlineKeyboardButton("➖","-")],
        [InlineKeyboardButton("0️⃣","0"), InlineKeyboardButton(".", "."), InlineKeyboardButton("🟰","="), InlineKeyboardButton("➕","+")],
        [InlineKeyboardButton("🔙","back"), InlineKeyboardButton("🧹","C")]
    ])

def display(expr):
    return f"🧮 *Calculator*\n\n`{expr if expr else '0'}`"

# =========================
# HANDLERS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id] = ""
    await update.message.reply_text(display(""), reply_markup=keyboard(), parse_mode="Markdown")

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
# EVENT LOOP FIX
# =========================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# =========================
# WEBHOOK (FINAL FIX)
# =========================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)

    # ✅ USE SAME LOOP
    loop.create_task(application.process_update(update))

    return "ok"

@app.route("/")
def home():
    return "Calculator Running ✅"

# =========================
# START BOT
# =========================
def start_bot():
    async def main():
        await application.initialize()
        await application.start()
        await application.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")

        while True:
            await asyncio.sleep(3600)

    loop.run_until_complete(main())

# =========================
# START
# =========================
if __name__ == "__main__":

    import threading

    threading.Thread(target=start_bot).start()

    port = int(os.environ.get("PORT", 10000))
    print("PORT:", port)

    app.run(host="0.0.0.0", port=port)
