"""
Kiyim do'koni boti.
O'rnatish:  pip install python-telegram-bot==21.6
Muhit o'zgaruvchilari (kodga yozmang, hosting panelidagi "Environment" qismiga kiriting):
  BOT_TOKEN   - @BotFather bergan token
  ADMIN_ID    - sizning Telegram ID raqamingiz (@userinfobot dan bilib oling)
  WEBAPP_URL  - index.html joylangan https manzil
  CARD_INFO   - mijoz to'lov qiladigan karta, masalan: 8600 1234 5678 9012 (Ism Familiya)
"""
import json
import os
import time

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
WEBAPP_URL = os.environ["WEBAPP_URL"]
CARD = os.getenv("CARD_INFO", "Karta raqami hali kiritilmagan")


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " so'm"


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("🛍 Do'konni ochish", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True,
    )
    await update.message.reply_text(
        "Salom! Kiyimlarni ko'rish va buyurtma berish uchun pastdagi tugmani bosing.",
        reply_markup=kb,
    )


async def on_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    o = json.loads(update.message.web_app_data.data)
    user = update.effective_user
    order_id = int(time.time()) % 1_000_000  # oddiy buyurtma raqami

    items = "\n".join(f"• {i['n']} ({i['s']}) × {i['q']} = {fmt(i['p'] * i['q'])}" for i in o["items"])
    total = sum(i["p"] * i["q"] for i in o["items"])  # jamini bot o'zi qayta hisoblaydi

    # Egasiga xabar
    await ctx.bot.send_message(
        ADMIN_ID,
        f"🆕 Yangi buyurtma #{order_id}\n\n{items}\n\nJami: {fmt(total)}\n\n"
        f"Ism: {o['name']}\nTelefon: {o['phone']}\nManzil: {o['addr']}\n"
        f"Telegram: @{user.username or '—'} (id {user.id})",
    )
    # Mijozga javob
    await update.message.reply_text(
        f"Buyurtmangiz #{order_id} qabul qilindi ✅\n\n{items}\n\nJami: {fmt(total)}\n\n"
        f"To'lov uchun kartaga o'tkazing:\n{CARD}\n\n"
        "To'lov chekining rasmini shu yerga yuboring. Tasdiqlangach siz bilan bog'lanamiz."
    )


async def on_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Mijoz yuborgan chek rasmini egasiga uzatadi."""
    await update.message.forward(ADMIN_ID)
    await update.message.reply_text("Chek qabul qilindi, tez orada tasdiqlaymiz 🙏")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_order))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.run_polling()


if __name__ == "__main__":
    main()
