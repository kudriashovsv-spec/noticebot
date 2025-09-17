import asyncio
import json
import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from datetime import datetime

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь для хранения напоминаний
reminders = {}

# Файл для хранения напоминаний
DATA_FILE = "reminders.json"

def save_reminders():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        # Сериализуем datetime в строку
        json.dump({str(k): [{"time": r["time"].isoformat(), "text": r["text"]} 
                             for r in v] 
                   for k, v in reminders.items()}, f, ensure_ascii=False, indent=4)

def load_reminders():
    global reminders
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            reminders = {}
            for k, v in data.items():
                user_reminders = []
                for r in v:
                    reminder_time = datetime.fromisoformat(r["time"])
                    reminder_text = r["text"]
                    sent = r.get("sent", False)
                    # Если время уже прошло, отмечаем как отправленное
                    if reminder_time <= datetime.now():
                        sent = True
                    user_reminders.append({
                        "time": reminder_time,
                        "text": reminder_text,
                        "sent": sent
                    })
                reminders[int(k)] = user_reminders


# --- Команды /start list done help clear edit---
@dp.message(Command("start", ignore_case=True))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Введи дату и время напоминания в формате ГГГГ-ММ-ДД ЧЧ:ММ, текст напоминания.\n"
        "Пример: 2025-09-09 15:00, Позвонить маме")

@dp.message(Command("list", ignore_case=True))
async def list_reminders(message: types.Message):
    user_id = message.from_user.id

    if user_id not in reminders or not reminders[user_id]:
        await message.answer("У тебя пока нет напоминаний 📭")
        return

    # Разделяем активные и выполненные
    active = [r for r in reminders[user_id] if not r.get("sent")]
    done = [r for r in reminders[user_id] if r.get("sent")]

    # Сортируем по времени
    active.sort(key=lambda r: r["time"])
    done.sort(key=lambda r: r["time"])

    text = ""

    if active:
        text += "⏰ <b>Активные напоминания:</b>\n"
        for idx, r in enumerate(active, start=1):
            text += f"{idx}. {r['time'].strftime('%Y-%m-%d %H:%M')} — {r['text']}\n"

    if done:
        text += "\n✅ <b>Выполненные напоминания:</b>\n"
        for idx, r in enumerate(done, start=1):
            text += f"{idx}. {r['time'].strftime('%Y-%m-%d %H:%M')} — {r['text']}\n"

    await message.answer(text, parse_mode="HTML")

@dp.message(Command("done", ignore_case=True))
async def done_reminder(message: types.Message):
    user_id = message.from_user.id

    if user_id not in reminders or not reminders[user_id]:
        await message.answer("У тебя пока нет напоминаний 📭")
        return

    # Только активные
    active = [r for r in reminders[user_id] if not r.get("sent")]
    done = [r for r in reminders[user_id] if r.get("sent")]

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

    if not completed:
        await message.answer("❗ Не было выбрано корректных напоминаний для выполнения")
        return

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

    # Только активные
    active = [r for r in reminders[user_id] if not r.get("sent")]

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "❗ Формат неверный! Используй: /edit <номер> <новое время или текст>\n"
            "Пример: /edit 1 2025-09-17 12:00, Позвонить другу"
        )
        return

    try:
        idx = int(parts[1]) - 1
        if idx < 0 or idx >= len(active):
            raise IndexError
    except (ValueError, IndexError):
        await message.answer("❗ Неверный номер напоминания")
        return

    new_data = parts[2].strip()
    if "," not in new_data:
        await message.answer("❗ Формат неверный! Используй: ГГГГ-ММ-ДД ЧЧ:ММ, текст напоминания")
        return

    date_str, reminder_text = map(str.strip, new_data.split(",", 1))
    try:
        new_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer("❗ Неверный формат даты! Пример: 2025-09-17 12:00, Позвонить другу")
        return

    # Обновляем активное напоминание
    reminder = active[idx]
    reminder["time"] = new_time
    reminder["text"] = reminder_text

    save_reminders()

    await message.answer(f"✅ Напоминание обновлено!\n⏰ {new_time.strftime('%Y-%m-%d %H:%M')} — {reminder_text}")

    
    # Обновляем списки
    active = [r for r in reminders[user_id] if not r.get("sent")]
    done = [r for r in reminders[user_id] if r.get("sent")]

    text = ""
    if active:
        text += "⏰ <b>Активные напоминания:</b>\n"
        for i, r in enumerate(active, start=1):
            text += f"{i}. {r['time'].strftime('%Y-%m-%d %H:%M')} — {r['text']}\n"

    if done:
        text += "\n✅ <b>Выполненные напоминания:</b>\n"
        for i, r in enumerate(done, start=1):
            text += f"{i}. {r['time'].strftime('%Y-%m-%d %H:%M')} — {r['text']}\n"

    await message.answer(
        f"✅ Выполнены напоминания:\n- " + "\n- ".join(completed) + f"\n\n{text}",
        parse_mode="HTML"
    )

@dp.message(Command("help", ignore_case=True))
async def cmd_help(message: types.Message):
    await message.answer(
    "<b>Список команд:</b>\n"
    "<code>/start</code> - начать работу с ботом\n"
    "<code>/list</code> - показать все напоминания\n"
    "<code>/done</code> - отметить напоминание как выполненное\n"
    "<code>/help</code> - показать список команд",
    parse_mode="HTML"
    )

# --- Добавление напоминания ---
@dp.message(~Command("start"), ~Command("list"), ~Command("done"), ~Command("help"))
async def add_reminder(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()  # убираем лишние пробелы

    if "," not in text:
        await message.answer(
            "❗ Формат неверный! Используй: ГГГГ-ММ-ДД ЧЧ:ММ, текст напоминания"
        )
        return

    date_str, reminder_text = map(str.strip, text.split(",", 1))  # чистим обе части

    try:
        reminder_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(
            "❗ Неверный формат даты! Пример: 2025-09-16 18:00, Позвонить маме"
        )
        return

    if user_id not in reminders:
        reminders[user_id] = []

    reminders[user_id].append({
        "time": reminder_time,
        "text": reminder_text
    })
    save_reminders()  # сохраняем изменения

    await message.answer(
        f"✅ Напоминание добавлено!\n"
        f"⏰ Время: {reminder_time.strftime('%Y-%m-%d %H:%M')}\n"
        f"📝 Текст: {reminder_text}"
    )




# --- Фоновая проверка напоминаний ---
async def reminder_checker():
    while True:  # бесконечный цикл
        now = datetime.now()  # текущее время
        for user_id, user_reminders in reminders.items():
            for reminder in user_reminders:
                # если время напоминания пришло или прошло
                if reminder["time"] <= now and not reminder.get("sent"):
                    await bot.send_message(user_id, f"Напоминание: {reminder['text']}")
                    reminder["sent"] = True  # отмечаем, что отправили
        await asyncio.sleep(30)  # проверяем каждые 30 секунд

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
