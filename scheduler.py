from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone, timedelta

# dateutil удобен для корректного парсинга ISO-дат из Google Calendar
from dateutil import parser

# Google Calendar API
from googleapiclient.discovery import build

# Логгер
from logger import logger

# Работа с базой данных
from database import (
    get_token,
    get_reminder,
    is_event_notified,
    mark_event_notified,
    save_event_history,
    is_event_in_history
)

# Авторизация Google Calendar
from google_calendar import authorize


# ---------- Google Calendar ----------
def get_events(creds, time_min=None, time_max=None, max_results=20):

   # Получение списка событий Google Calendar за указанный период времени.

    service = build("calendar", "v3", credentials=creds)

    events = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
        maxResults=max_results
    ).execute()

    return events.get("items", [])


# ---------- Основная задача планировщика ----------
async def check_events(bot):
    
    from database import cursor

    logger.info("Scheduler tick started")

    # Получаем всех пользователей бота
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    # Текущее время в UTC (для корректных сравнений)
    now = datetime.now(timezone.utc)

    for (user_id,) in users:
        token = get_token(user_id)
        if not token:
            # Пользователь ещё не подключил календарь
            continue

        reminder_minutes = get_reminder(user_id)

        # Авторизация Google Calendar для конкретного пользователя
        creds = authorize(token)

        # Берём события в диапазоне вокруг текущего времени

        time_min = (now - timedelta(hours=2)).isoformat()
        time_max = (now + timedelta(hours=6)).isoformat()

        events = get_events(creds, time_min, time_max)

        for event in events:
            event_id = event.get("id")
            summary = event.get("summary", "Без названия")
            link = event.get("htmlLink")

            start_str = event.get("start", {}).get("dateTime")
            end_str = event.get("end", {}).get("dateTime")

            # Пропускаем некорректные события (all-day и т.п.)
            if not event_id or not start_str or not end_str:
                continue

            # Время начала и окончания встречи
            start_time = parser.isoparse(start_str)
            end_time = parser.isoparse(end_str)

            # ---------- 1. УВЕДОМЛЕНИЕ ----------
            delta = start_time - now

            # Проверяем что событие скоро начнётся и пользователь ещё не получал уведомление
            if (
                0 < delta.total_seconds() <= reminder_minutes * 60
                and not is_event_notified(user_id, event_id)
            ):
                # Приводим время к таймзоне системы
                offset_hours = int(start_time.utcoffset().total_seconds() / 3600)
                tz_label = f"UTC{offset_hours:+d}"

                await bot.send_message(
                    user_id,
                    "⏰ Напоминание!\n"
                    f"Встреча: {summary}\n"
                    f"Время: {start_time.strftime('%d.%m.%Y %H:%M')} ({tz_label})\n"
                    f"Ссылка: {link}"
                )

                logger.info(
                    f"Notification sent user={user_id}, event={event_id}"
                )

                # Помечаем событие как уведомлённое
                mark_event_notified(user_id, event_id)

            # ---------- 2. ИСТОРИЯ (ПОСЛЕ ЗАВЕРШЕНИЯ) ----------
            # Добавляем событие в историю только после его окончания
            if end_time < now:
                local_end = end_time.astimezone()
                end_str_fmt = local_end.strftime("%d.%m.%Y %H:%M")

                # Проверяем, что событие ещё не добавлено в историю
                if not is_event_in_history(user_id, end_str_fmt, summary):
                    save_event_history(
                        user_id=user_id,
                        event_id=event_id,
                        event_time=end_str_fmt,
                        summary=summary
                    )

                    logger.info(
                        f"History saved user={user_id}, event={event_id}"
                    )


# ---------- Планировщик ----------
def start_scheduler(bot):

    # Запуск APScheduler для периодической проверки событий.

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        check_events,
        trigger="interval",
        minutes=1,          # Проверка раз в минуту
        args=[bot],
        max_instances=1     # Защита от параллельного выполнения
    )

    scheduler.start()
