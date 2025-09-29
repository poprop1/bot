import json
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters
)

DATA_FILE = "streak.json"
FILES_PER_DAY = 6
MAX_STREAK = 16
TOKEN = "8413011096:AAHP-xUkdSOU0FXhZ3_yYX-RS7FaAJ6AZXo"

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"streak": 0, "last_day": None, "files_today": 0, "message_id": None, "chat_id": None}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Скинуть стрик", callback_data="reset_streak")]
    ])

async def update_streak_message(app, data):
    streak = data.get("streak", 0)
    files_today = data.get("files_today", 0)
    emoji = "🔥" if files_today == FILES_PER_DAY else "⌛"

    if streak >= MAX_STREAK:
        text = f"🎉 Молодец! Все сдано! Стрик: {streak}🔥"
    else:
        text = f"🔥 Текущий стрик: {streak}{emoji}\nФайлы сегодня: {files_today}/{FILES_PER_DAY}"

    chat_id = data.get("chat_id")
    message_id = data.get("message_id")

    if chat_id:
        try:
            if message_id:
                await app.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=get_keyboard())
            else:
                msg = await app.bot.send_message(chat_id=chat_id, text=text, reply_markup=get_keyboard())
                await app.bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id)
                data["message_id"] = msg.message_id
                save_data(data)
        except:
            msg = await app.bot.send_message(chat_id=chat_id, text=text, reply_markup=get_keyboard())
            await app.bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id)
            data["message_id"] = msg.message_id
            save_data(data)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    data["chat_id"] = update.effective_chat.id

    today = str(datetime.date.today())
    if data.get("last_day") != today:
        data["files_today"] = 0
        data["last_day"] = today

    save_data(data)

    await update.message.reply_text(
        f"Привет! Я бот для стриков.\nПрисылай {FILES_PER_DAY} файлов или скриншотов в день, чтобы увеличить стрик."
    )
    await update_streak_message(context.application, data)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    today = str(datetime.date.today())

    # Новый день: проверяем, завершен ли предыдущий
    if data.get("last_day") != today:
        if data.get("files_today", 0) < FILES_PER_DAY and data.get("streak", 0) > 0:
            data["streak"] = 0
            await update.message.reply_text(
                "⏳ Время платить по счетам! Стрик сброшен, можно продолжить заново."
            )
        data["files_today"] = 0
        data["last_day"] = today

    if update.message.document or update.message.photo:
        data["files_today"] = data.get("files_today", 0) + 1
        save_data(data)

        if data["files_today"] < FILES_PER_DAY:
            await update.message.reply_text(f"Файлы сегодня: {data['files_today']}/{FILES_PER_DAY}")
        else:
            # День завершен
            data["streak"] = data.get("streak", 0) + 1
            await update.message.reply_text(f"✅ День закрыт! Стрик: {data['streak']}🔥")
            # После завершения дня сразу начинается новый день
            data["files_today"] = 0
            data["last_day"] = today
            save_data(data)

        # Обновляем закрепленное сообщение сразу
        await update_streak_message(context.application, data)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()

    if query.data == "reset_streak":
        data["streak"] = 0
        data["files_today"] = 0
        save_data(data)
        await query.message.reply_text("⚠️ Стрик был сброшен!")
        await update_streak_message(context.application, data)

def main():
    app = ApplicationBuilder().token(TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
