import asyncio
from datetime import datetime

# Aiogram — работа с Telegram Bot API
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

# Планировщик фоновых задач
from scheduler import start_scheduler

# Работа с Google Calendar
from google_calendar import get_past_events, authorize

# Работа с базой данных
from database import (
    save_event_history,
    save_token,
    get_token,
    set_reminder,
    get_history
)

# Логирование
from logger import logger

# Конфигурация
from config import BOT_TOKEN


async def main():

    #Инициализирует бота, регистрирует команды и запускает планировщик.

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # ---------- /start ----------
    @dp.message(Command("start"))
    async def start_handler(message: Message):
    
        #Показывает список доступных команд.

        logger.info(f"/start user={message.from_user.id}")

        await message.answer(
            "Привет! 👋\n"
            "Я бот для уведомлений из Google Calendar.\n\n"
            "Команды:\n"
            "/set_reminder <минуты> — за сколько минут напоминать\n"
            "/history — показать историю встреч\n"
            "/connect_calendar — подключить Google Calendar\n"
        )

    # ---------- /connect_calendar ----------
    @dp.message(Command("connect_calendar"))
    async def connect_calendar(message: Message):
       
        # Подключение Google Calendar через OAuth. Сохраняет токен пользователя и загружает историю прошедших встреч.

        await message.answer("🔐 Подключение Google Calendar...")

        # Авторизация (если токен есть — используется, если нет — OAuth)
        creds = authorize(get_token(message.from_user.id))

        # Сохраняем OAuth-токен пользователя
        save_token(message.from_user.id, creds.to_json())

        # Загружаем события за последние 7 дней для истории
        past_events = get_past_events(creds, days=7)

        for event in past_events:
            event_id = event.get("id")
            if not event_id:
                continue

            end = event.get("end", {}).get("dateTime")
            if not end:
                continue

            # Время окончания встречи (UTC → datetime)
            end_time = datetime.fromisoformat(end.replace("Z", "+00:00"))

            # Сохраняем событие в историю
            save_event_history(
                message.from_user.id,
                event_id,
                end_time.strftime("%d.%m.%Y %H:%M"),
                event.get("summary", "Без названия")
            )

        await message.answer("✅ Календарь подключён и история обновлена!")
        logger.info(f"Calendar connected user={message.from_user.id}")

    # ---------- /set_reminder ----------
    @dp.message(Command("set_reminder"))
    async def reminder_handler(message: Message):
  
        # Устанавливает время напоминания в минутах до начала встречи.

        try:
            minutes = int(message.text.split()[1])
            if minutes <= 0:
                raise ValueError

            set_reminder(message.from_user.id, minutes)
            await message.answer(f"⏰ Напоминание установлено за {minutes} минут")

        except (IndexError, ValueError):
            await message.answer(
                "❌ Использование:\n"
                "/set_reminder <минуты>\n"
                "Пример: /set_reminder 15"
            )

    # ---------- /history ----------
    @dp.message(Command("history"))
    async def history_handler(message: Message):

        # Показывает последние 10 завершённых встреч пользователя.

        history = get_history(message.from_user.id)

        if not history:
            await message.answer("История встреч пуста.")
            return

        text = "Последние 10 встреч:\n\n"
        for i, (time, summary) in enumerate(history, 1):
            text += f"{i}. [{time}] {summary}\n"

        await message.answer(text)

    # ---------- Запуск ----------
    print("Бот запущен...")

    # Запускаем планировщик фоновой проверки событий
    start_scheduler(bot)

    # Запускаем обработку сообщений Telegram
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
