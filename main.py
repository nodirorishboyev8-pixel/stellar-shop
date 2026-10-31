"""
Stellar do'kon boti (3-versiya):
- har buyurtmaga takrorlanmas raqam (orders.json da saqlanadi)
- tasdiqlash tugmalari har buyurtmaga alohida ishlaydi
- lokatsiya (mini ilovadan yoki bot orqali) + Yandex Xarita havolasi
Wispbyte'da shu fayl nomi main.py bo'lishi kerak.
"""
import json
import os
import time
from pathlib import Path

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ===== SHU 4 QATORNI O'ZINGIZNIKIGA ALMASHTIRING =====
TOKEN = "9167660799:AAEYHDGc84NzUmJyLe1fOR11ZU2r63X_gFM"
ADMIN_ID = 5764255493
WEBAPP_URL = "https://nodirorishboyev8-pixel.github.io/stellar-shop/"
CARD = "4073 4200 6189 7157 (Nodir O'rishboyev)"
# Kanal yoki guruh ID si (masalan -1001234567890). 0 bo'lsa, o'chirilgan.
CHANNEL_ID = -1004486543583
# =====================================================

DB_FILE = Path(__file__).with_name("orders.json")
STATUS_TEXT = {
    "new": "🆕 yangi",
    "ok": "✅ tasdiqlangan",
    "shipped": "🚚 yo'lda",
    "cancelled": "❌ bekor qilingan",
}


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " so'm"


def load_db() -> dict:
    try:
        return json.loads(DB_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"last_id": 1000, "orders": {}, "last_by_user": {}}


def save_db(db: dict) -> None:
    tmp = DB_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(db, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, DB_FILE)  # fayl yarim yozilib qolmasligi uchun


def yandex_link(lat: float, lon: float) -> str:
    # Yandex'da tartib: uzunlik (lon), keyin kenglik (lat)
    return f"https://yandex.com/maps/?pt={lon},{lat}&z=17&l=map"


def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🛍 Do'konni ochish", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True,
    )


async def to_channel(ctx, text=None, loc=None):
    """Kanal/guruhga nusxa yuboradi. Xato bo'lsa ham buyurtma to'xtamaydi."""
    if not CHANNEL_ID:
        return None
    try:
        msg = await ctx.bot.send_message(CHANNEL_ID, text) if text else None
        if loc:
            await ctx.bot.send_location(CHANNEL_ID, loc[0], loc[1])
        return msg.message_id if msg else None
    except Exception as e:
        print("Kanalga yuborib bo'lmadi:", e)
        return None


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Kiyimlarni ko'rish va buyurtma berish uchun pastdagi tugmani bosing.",
        reply_markup=main_kb(),
    )


async def on_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    o = json.loads(update.message.web_app_data.data)
    user = update.effective_user
    loc = o.get("loc")

    # Takrorlanmas raqam: hisoblagich faylda saqlanadi
    db = load_db()
    db["last_id"] += 1
    order_id = db["last_id"]
    total = sum(i["p"] * i["q"] for i in o["items"])
    db["orders"][str(order_id)] = {
        "uid": user.id,
        "name": o["name"],
        "total": total,
        "status": "new",
        "time": int(time.time()),
    }
    db["last_by_user"][str(user.id)] = order_id
    save_db(db)

    items = "\n".join(
        f"• {i['n']} ({i['s']}) × {i['q']} = {fmt(i['p'] * i['q'])}" for i in o["items"]
    )
    loc_line = f"\nLokatsiya: {yandex_link(loc['lat'], loc['lon'])}" if loc else ""

    buttons = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"ok:{user.id}:{order_id}"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data=f"no:{user.id}:{order_id}"),
        ]]
    )
    text = (
        f"🆕 Yangi buyurtma #{order_id}\n\n{items}\n\nJami: {fmt(total)}\n\n"
        f"Ism: {o['name']}\nTelefon: {o['phone']}\nManzil: {o['addr']}{loc_line}\n"
        f"Telegram: @{user.username or '—'} (id {user.id})"
    )
    await ctx.bot.send_message(ADMIN_ID, text, reply_markup=buttons)
    if loc:
        await ctx.bot.send_location(ADMIN_ID, loc["lat"], loc["lon"])

    # Kanal/guruhga nusxa (tugmasiz); xabar raqamini holat yangilash uchun saqlaymiz
    ch_msg = await to_channel(ctx, text, (loc["lat"], loc["lon"]) if loc else None)
    if ch_msg:
        db = load_db()
        db["orders"][str(order_id)]["ch_msg"] = ch_msg
        save_db(db)

    await update.message.reply_text(
        f"Buyurtmangiz #{order_id} qabul qilindi ✅\n\n{items}\n\nJami: {fmt(total)}\n\n"
        f"To'lov uchun kartaga o'tkazing:\n{CARD}\n\n"
        "To'lov chekining rasmini shu yerga yuboring. Tasdiqlangach xabar beramiz.",
        reply_markup=main_kb(),
    )

    # Lokatsiya belgilanmagan bo'lsa, bot orqali so'raymiz
    if not loc:
        kb = ReplyKeyboardMarkup(
            [
                [KeyboardButton("📍 Lokatsiyani yuborish", request_location=True)],
                ["Hozir emas"],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await update.message.reply_text(
            "Kuryer manzilni oson topishi uchun lokatsiyangizni yuboring (ixtiyoriy).",
            reply_markup=kb,
        )


async def on_location(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Mijoz lokatsiya yubordi: oxirgi buyurtmasiga bog'lab egasiga yuboramiz."""
    user = update.effective_user
    loc = update.message.location
    db = load_db()
    oid = db["last_by_user"].get(str(user.id))
    if not oid:
        await update.message.reply_text("Avval buyurtma bering.", reply_markup=main_kb())
        return
    await ctx.bot.send_message(
        ADMIN_ID,
        f"📍 Buyurtma #{oid} lokatsiyasi\nMijoz: {user.full_name} (id {user.id})\n"
        f"{yandex_link(loc.latitude, loc.longitude)}",
    )
    await ctx.bot.send_location(ADMIN_ID, loc.latitude, loc.longitude)
    await to_channel(
        ctx,
        f"📍 Buyurtma #{oid} lokatsiyasi\n{yandex_link(loc.latitude, loc.longitude)}",
        (loc.latitude, loc.longitude),
    )
    await update.message.reply_text("Lokatsiya qabul qilindi 📍", reply_markup=main_kb())


async def on_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Xo'p, mayli.", reply_markup=main_kb())


async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("Ruxsat yo'q", show_alert=True)
        return

    action, uid, oid = q.data.split(":")
    uid = int(uid)

    # Holatlar tartibi: new -> ok -> shipped; bekor qilish new/ok dan
    allowed = {"ok": {"new"}, "ship": {"ok"}, "no": {"new", "ok"}}
    new_status = {"ok": "ok", "ship": "shipped", "no": "cancelled"}[action]

    db = load_db()
    rec = db["orders"].get(oid)
    if rec and rec["status"] not in allowed[action]:
        await q.answer(f"Bu buyurtma allaqachon: {STATUS_TEXT[rec['status']]}", show_alert=True)
        return

    if action == "ok":
        status = "✅ TASDIQLANDI"
        to_user = f"Buyurtmangiz #{oid} tasdiqlandi ✅\nTez orada yetkazib berishga tayyorlaymiz."
        next_kb = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("🚚 Yo'lga chiqdi", callback_data=f"ship:{uid}:{oid}"),
                InlineKeyboardButton("❌ Bekor qilish", callback_data=f"no:{uid}:{oid}"),
            ]]
        )
    elif action == "ship":
        status = "🚚 YO'LGA CHIQDI"
        to_user = f"Buyurtmangiz #{oid} yo'lga chiqdi 🚚\nKuryer siz bilan bog'lanadi."
        next_kb = None
    else:
        status = "❌ BEKOR QILINDI"
        to_user = f"Afsuski, buyurtmangiz #{oid} bekor qilindi. Savollar bo'lsa, bizga yozing."
        next_kb = None

    if rec:
        rec["status"] = new_status
        save_db(db)

    try:
        await ctx.bot.send_message(uid, to_user)
        await q.answer("Mijozga xabar yuborildi")
    except Exception:
        await q.answer("Mijozga xabar yetmadi (botni bloklagan bo'lishi mumkin)", show_alert=True)

    base = q.message.text.split("\n\nHolat:")[0]
    await q.edit_message_text(f"{base}\n\nHolat: {status}", reply_markup=next_kb)

    # Kanaldagi nusxada ham holatni yangilaymiz
    if CHANNEL_ID and rec and rec.get("ch_msg"):
        try:
            await ctx.bot.edit_message_text(
                f"{base}\n\nHolat: {status}", chat_id=CHANNEL_ID, message_id=rec["ch_msg"]
            )
        except Exception as e:
            print("Kanal xabarini yangilab bo'lmadi:", e)


async def on_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Chek rasmini egasiga yuboradi, mijozning oxirgi buyurtma raqami bilan."""
    user = update.effective_user
    oid = load_db()["last_by_user"].get(str(user.id))
    order_part = f" (buyurtma #{oid})" if oid else ""
    await ctx.bot.send_photo(
        ADMIN_ID,
        update.message.photo[-1].file_id,
        caption=(
            f"🧾 To'lov cheki{order_part}\n"
            f"Mijoz: {user.full_name} @{user.username or '—'} (id {user.id})"
        ),
    )
    await update.message.reply_text("Chek qabul qilindi, tez orada tasdiqlaymiz 🙏")


async def orders_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/orders: oxirgi 10 ta buyurtma (faqat admin)."""
    if update.effective_user.id != ADMIN_ID:
        return
    db = load_db()
    ids = sorted(db["orders"], key=int, reverse=True)[:10]
    if not ids:
        await update.message.reply_text("Hozircha buyurtma yo'q.")
        return
    lines = [
        f"#{i} · {db['orders'][i]['name']} · {fmt(db['orders'][i]['total'])} · "
        f"{STATUS_TEXT[db['orders'][i]['status']]}"
        for i in ids
    ]
    await update.message.reply_text("Oxirgi buyurtmalar:\n\n" + "\n".join(lines))


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("orders", orders_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_order))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.LOCATION, on_location))
    app.add_handler(MessageHandler(filters.Regex("^Hozir emas$"), on_skip))
    app.run_polling()


if __name__ == "__main__":
    main()
