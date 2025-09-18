import asyncio
import json
import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь для хранения напоминаний
reminders = {}

# Файл для хранения напоминаний
DATA_FILE = "reminders.json"

def save_reminders():
    data = {}
    for user_id, user_reminders in reminders.items():
        data[user_id] = []
        for r in user_reminders:
            data[user_id].append({
                "time": r["time"].strftime("%d.%m.%Y %H:%M"),
                "text": r["text"],
                "repeat": r.get("repeat"),  # добавили повторение
                "sent": r["sent"]
            })
    with open("reminders.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_reminders():
    global reminders
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            reminders = {}
            for user_id, user_reminders in data.items():
                reminders[user_id] = []
                for r in user_reminders:
                    reminders[user_id].append({
                        "time": datetime.strptime(r["time"], "%d.%m.%Y %H:%M"),  # ✅ исправлено
                        "text": r["text"],
                        "repeat": r.get("repeat"),
                        "sent": r.get("sent", False)
                    })
    except FileNotFoundError:
        reminders = {}


# --- Команды /start list done help clear edit---
@dp.message(Command("start", ignore_case=True))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Введи дату и время напоминания в формате ДД.MM.ГГГГ ЧЧ:ММ, текст напоминания.\n"
        "Пример: 18.09.2025 15:00 Позвонить маме")

@dp.message(Command("list", ignore_case=True))
async def list_reminders(message: types.Message):
    user_id = message.from_user.id

    # Проверяем, есть ли у пользователя напоминания
    if user_id not in reminders or not reminders[user_id]:
        await message.answer("У тебя пока нет напоминаний 📭")
        return

    # Разделяем на активные и выполненные напоминания
    active = [r for r in reminders[user_id] if not r.get("sent")]
    done = [r for r in reminders[user_id] if r.get("sent")]

    # Сортируем по времени
    active.sort(key=lambda r: r["time"])
    done.sort(key=lambda r: r["time"])

    # ----------------------------
    # 1️⃣ Работаем с активными напоминаниями
    # ----------------------------
    if active:
        buttons = [
            [InlineKeyboardButton(text=f"✅ {r['time'].strftime('%d.%m.%Y %H:%M')} — {r['text']}", callback_data=f"done_{i}")]
            for i, r in enumerate(active)  # start=0 по умолчанию
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(
            "⏰ <b>Активные напоминания:</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message.answer("У тебя пока нет активных напоминаний ⏰")


    # ----------------------------
    # 2️⃣ Работаем с выполненными напоминаниями
    # ----------------------------
    if done:
        text_done = "✅ <b>Выполненные напоминания:</b>\n"
        for i, r in enumerate(done, start=1):
            text_done += f"{i}. {r['time'].strftime('%d.%m.%Y %H:%M')} — {r['text']}"
            if r.get("repeat"):
                text_done += f" 🔁 {r['repeat']}"
            text_done += "\n"
        await message.answer(text_done, parse_mode="HTML")

@dp.message(Command("done", ignore_case=True))
async def done_reminder(message: types.Message):
    user_id = message.from_user.id

    if user_id not in reminders or not reminders[user_id]:
        await message.answer("У тебя пока нет напоминаний 📭")
        return

    active = [r for r in reminders[user_id] if not r.get("sent")]

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❗ Укажи номера активных напоминаний, например: /done 1 2")
        return

    completed = []
    for part in parts[1:]:
        try:
            idx = int(part) - 1
            if idx < 0 or idx >= len(active):
                raise IndexError
            reminder = active[idx]
            reminder["sent"] = True
            completed.append(reminder["text"])
        except (ValueError, IndexError):
            await message.answer(f"❗ Игнорирован неверный номер: {part}")

    save_reminders()

    if completed:
        await message.answer("✅ Выполнены напоминания:\n- " + "\n- ".join(completed))
    else:
        await message.answer("❗ Не было выбрано корректных напоминаний для выполнения")

# --- Команда /clear ---
@dp.message(Command("clear", ignore_case=True))
async def clear_done_reminders(message: types.Message):
    user_id = message.from_user.id

    if user_id not in reminders or not reminders[user_id]:
        await message.answer("У тебя пока нет напоминаний 📭")
        return

    before_count = len(reminders[user_id])
    reminders[user_id] = [r for r in reminders[user_id] if not r.get("sent")]
    removed_count = before_count - len(reminders[user_id])
    
    save_reminders()
    
    await message.answer(f"✅ Удалено {removed_count} выполненных напоминаний.")

# --- Команда /edit ---
@dp.message(Command("edit", ignore_case=True))
async def edit_reminder(message: types.Message):
    user_id = message.from_user.id

    if user_id not in reminders or not reminders[user_id]:
        await message.answer("У тебя пока нет напоминаний 📭")
        return

    active = [r for r in reminders[user_id] if not r.get("sent")]

    if not active:
        await message.answer("У тебя пока нет активных напоминаний ⏰")
        return

    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        # Выводим список активных напоминаний для удобства
        text = "⏰ <b>Активные напоминания:</b>\n"
        for i, r in enumerate(active, start=1):
            text += f"{i}. {r['time'].strftime('%d.%m.%Y %H:%M')} — {r['text']}\n"
        text += "\n❗ Используй: /edit <номер> ДД.MM.ГГГГ ЧЧ:ММ Новый текст"
        await message.answer(text, parse_mode="HTML")
        return

    try:
        idx = int(parts[1]) - 1
        if idx < 0 or idx >= len(active):
            raise IndexError
    except (ValueError, IndexError):
        await message.answer("❗ Неверный номер напоминания")
        return

    date_str = parts[2]
    time_str = parts[3].split()[0]
    reminder_text = " ".join(parts[3].split()[1:])

    try:
        new_time = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer("❗ Неверный формат даты! Пример: 18.09.2025 12:00 Сделать звонок")
        return

    reminder = active[idx]
    reminder["time"] = new_time
    reminder["text"] = reminder_text
    save_reminders()

    await message.answer(f"✅ Напоминание обновлено!\n⏰ {new_time.strftime('%d.%m.%Y %H:%M')} — {reminder_text}")


    
    # Обновляем списки
    active = [r for r in reminders[user_id] if not r.get("sent")]
    done = [r for r in reminders[user_id] if r.get("sent")]

    text = ""
    if active:
        text += "⏰ <b>Активные напоминания:</b>\n"
        for i, r in enumerate(active, start=1):
            text += f"{i}. {r['time'].strftime('%d.%m.%Y %H:%M')} — {r['text']}"
            if r.get("repeat"):
                text += f" 🔁 {r['repeat']}"
            text += "\n"

    if done:
        text += "\n✅ <b>Выполненные напоминания:</b>\n"
        for i, r in enumerate(done, start=1):
            text += f"{i}. {r['time'].strftime('%d.%m.%Y %H:%M')} — {r['text']}"
            if r.get("repeat"):
                text += f" 🔁 {r['repeat']}"
            text += "\n"

    await message.answer(text, parse_mode="HTML")

@dp.message(Command("help", ignore_case=True))
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 <b>Список команд:</b>\n"
        "👉 <code>/start</code> — начать работу с ботом\n"
        "👉 <code>/list</code> — показать все напоминания\n"
        "👉 <code>/done</code> — отметить напоминание как ✅ выполненное\n"
        "👉 <code>/clear</code> — удалить 🗑️ все выполненные напоминания\n"
        "👉 <code>/edit</code> — ✏️ изменить напоминание\n"
        "👉 <code>/help</code> — показать список команд\n\n"
        "⏰ <b>Добавление напоминания:</b>\n"
        "Просто напиши в чат:\n"
        "<code>18.09.2025 10:00 Сделать зарядку</code>\n\n"
        "🔁 <b>С повторением:</b>\n"
        "<code>18.09.2025 10:00 Сделать зарядку daily</code>\n"
        "Варианты повторения: <code>daily</code>, <code>weekly</code>, <code>monthly</code>",
        parse_mode="HTML"
    )

# --- Добавление напоминания ---
@dp.message(~Command("start"), ~Command("list"), ~Command("done"), ~Command("help"), ~Command("clear"), ~Command("edit"))
async def add_reminder(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip().split()  # разбиваем по пробелам

    if len(text) < 3:
        await message.answer(
            "❗ Формат неверный! Используй: ДД.MM.ГГГГ ЧЧ:ММ Текст напоминания [repeat]\n"
            "Пример: 18.09.2025 10:00 Сделать зарядку daily"
        )
        return

    date_str = text[0]
    time_str = text[1]
    reminder_text = " ".join(text[2:])  # всё остальное — текст

    repeat = None
    # Если в конце написано daily/weekly/monthly
    if reminder_text.split()[-1].lower() in ["daily", "weekly", "monthly"]:
        repeat = reminder_text.split()[-1].lower()
        reminder_text = " ".join(reminder_text.split()[:-1])

    try:
        reminder_time = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer("❗ Неверный формат даты! Пример: 18.09.2025 10:00 Сделать зарядку")
        return

    if user_id not in reminders:
        reminders[user_id] = []

    reminders[user_id].append({
        "time": reminder_time,
        "text": reminder_text,
        "repeat": repeat,
        "sent": False
    })
    save_reminders()

    reply_text = (
        f"✅ Напоминание добавлено!\n"
        f"⏰ Время: {reminder_time.strftime('%d.%m.%Y %H:%M')}\n"
        f"📝 Текст: {reminder_text}"
    )
    if repeat:
        reply_text += f"\n🔁 Повторение: {repeat}"

    await message.answer(reply_text)


# --- Фоновая проверка напоминаний ---
async def reminder_checker():
    while True:
        now = datetime.now()
        for user_id, user_reminders in reminders.items():
            for reminder in user_reminders:
                if reminder["time"] <= now and not reminder.get("sent"):
                    await bot.send_message(user_id, f"⏰ {reminder['time'].strftime('%d.%m.%Y %H:%M')} — {reminder['text']}")
                    reminder["sent"] = True

                    # --- создаём повторение ---
                    repeat = reminder.get("repeat")
                    if repeat == "daily":
                        reminder["time"] += timedelta(days=1)
                        reminder["sent"] = False
                    elif repeat == "weekly":
                        reminder["time"] += timedelta(weeks=1)
                        reminder["sent"] = False
                    elif repeat == "monthly":
                        # Для простоты добавим 30 дней
                        reminder["time"] += timedelta(days=30)
                        reminder["sent"] = False

                    save_reminders()

        await asyncio.sleep(30)  # проверка каждые 30 секунд

# === НОВЫЙ ОБРАБОТЧИК INLINE КНОПОК ===
@dp.callback_query(lambda c: c.data and c.data.startswith("done_"))
async def process_done_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in reminders:
        await callback_query.answer("❗ Напоминание не найдено", show_alert=True)
        return

    active = [r for r in reminders[user_id] if not r.get("sent")]
    index = int(callback_query.data.split("_")[1])  # индекс совпадает с enumerate(active)

    if index >= len(active):
        await callback_query.answer("❗ Напоминание не найдено", show_alert=True)
        return

    # Отмечаем как выполненное
    reminder = active[index]
    reminder["sent"] = True
    save_reminders()

    # Формируем новую клавиатуру без выполненного напоминания
    active = [r for r in reminders[user_id] if not r.get("sent")]
    if active:
        buttons = [
            [InlineKeyboardButton(text=f"✅ {r['time'].strftime('%d.%m.%Y %H:%M')} — {r['text']}", callback_data=f"done_{i}")]
            for i, r in enumerate(active)
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback_query.message.edit_text(
            "⏰ <b>Активные напоминания:</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await callback_query.message.edit_text(
            "Все напоминания выполнены! ✅",
            reply_markup=None
        )

    await callback_query.answer("✅ Напоминание отмечено как выполненное")



# --- Главная функция ---
async def main():
    load_reminders ()  # загружаем напоминания при старте
    print("Бот запущен")
    # Запускаем фоновую задачу параллельно с ботом
    asyncio.create_task(reminder_checker())
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
