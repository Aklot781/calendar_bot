import sqlite3
from logger import logger

# Подключение к SQLite базе данных
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

#аблица пользователей
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    token TEXT,
    reminder_minutes INTEGER DEFAULT 15
)
""")
conn.commit()


def save_token(user_id: int, token: str):
    # Создаём пользователя, если его ещё нет
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    # Сохраняем OAuth-токен
    cursor.execute(
        "UPDATE users SET token = ? WHERE user_id = ?",
        (token, user_id)
    )
    conn.commit()
    logger.info(f"Token saved for user={user_id}")


def get_token(user_id: int):
    # Получение сохранённого токена пользователя
    cursor.execute(
        "SELECT token FROM users WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def set_reminder(user_id: int, minutes: int):
    # Установка времени напоминания
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    cursor.execute(
        "UPDATE users SET reminder_minutes = ? WHERE user_id = ?",
        (minutes, user_id)
    )
    conn.commit()


def get_reminder(user_id: int):
    # Получение времени напоминания
    cursor.execute(
        "SELECT reminder_minutes FROM users WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else 15


# Таблица отправленных уведомлений
cursor.execute("""
CREATE TABLE IF NOT EXISTS notified_events (
    user_id INTEGER,
    event_id TEXT,
    PRIMARY KEY (user_id, event_id)
)
""")
conn.commit()


def is_event_notified(user_id: int, event_id: str) -> bool:
    # Проверка отправлялось ли уведомление
    cursor.execute(
        "SELECT 1 FROM notified_events WHERE user_id = ? AND event_id = ?",
        (user_id, event_id)
    )
    return cursor.fetchone() is not None


def mark_event_notified(user_id: int, event_id: str):
    # Пометка события как уведомлённого
    cursor.execute(
        "INSERT OR IGNORE INTO notified_events (user_id, event_id) VALUES (?, ?)",
        (user_id, event_id)
    )
    conn.commit()


# Таблица истории встреч
cursor.execute("""
CREATE TABLE IF NOT EXISTS events_history (
    user_id INTEGER,
    event_id TEXT,
    event_time TEXT,
    summary TEXT,
    PRIMARY KEY (user_id, event_id)
)
""")
conn.commit()


def save_event_history(user_id: int, event_id: str, event_time: str, summary: str):

    cursor.execute(
        """
        INSERT OR IGNORE INTO events_history
        (user_id, event_id, event_time, summary)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, event_id, event_time, summary)
    )
    conn.commit()

    # Удаляем лишние записи текущего пользователя
    cursor.execute("""
        DELETE FROM events_history
        WHERE user_id = ?
        AND rowid NOT IN (
            SELECT rowid FROM events_history
            WHERE user_id = ?
            ORDER BY event_time DESC
            LIMIT 10
        )
    """, (user_id, user_id))

    conn.commit()

    logger.info(
        f"Event saved to history user={user_id}, event={event_id}"
    )


def get_history(user_id: int):
    # Получение последних 10 встреч
    cursor.execute(
        "SELECT event_time, summary FROM events_history "
        "WHERE user_id = ? ORDER BY event_time DESC LIMIT 10",
        (user_id,)
    )
    return cursor.fetchall()


def is_event_in_history(user_id: int, event_time: str, summary: str) -> bool:
    # Проверка наличия события в истории
    cursor.execute(
        "SELECT 1 FROM events_history WHERE user_id = ? AND event_time = ? AND summary = ?",
        (user_id, event_time, summary)
    )
    return cursor.fetchone() is not None
