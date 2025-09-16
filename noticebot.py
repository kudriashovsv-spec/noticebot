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
            # Преобразуем строки обратно в datetime
            reminders = {int(k): [{"time": datetime.fromisoformat(r["time"]), "text": r["text"]} 
                                   for r in v] 
                         for k, v in data.items()}


# --- Команды /start list done help ---
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

    text = "📋 Твои напоминания:\n"
    for idx, r in enumerate(reminders[user_id], start=1):
        text += f"{idx}. {r['time']} — {r['text']}\n"

    await message.answer(text)

@dp.message(Command("done", ignore_case=True))
async def done_reminder(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❗ Укажи номер напоминания, например: /done 1")
        return

    user_id = message.from_user.id
    idx = int(parts[1]) - 1

    if user_id not in reminders or idx < 0 or idx >= len(reminders[user_id]):
        await message.answer("❗ Напоминания с таким номером нет")
        return

    removed = reminders[user_id].pop(idx)  # удаляем напоминание из списка
    save_reminders()  # сохраняем изменения в JSON
    await message.answer(f"✅ Удалено: {removed['text']}")

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
    try:
        text = message.text
        date_str, reminder_text = text.split(",", 1)
        reminder_time = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M")

        if user_id not in reminders:
            reminders[user_id] = []
        reminders[user_id].append({
            "time": reminder_time,
            "text": reminder_text.strip()
        })
        save_reminders()  # <-- вызываем после добавления

        await message.answer(f"Напоминание сохранено: {reminder_text.strip()} на {reminder_time}")

    except ValueError:
        await message.answer("Неверный формат! Используйте ГГГГ-ММ-ДД ЧЧ:ММ, текст напоминания")




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
