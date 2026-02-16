import json
from datetime import datetime, timedelta

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Область доступа
# readonly — только чтение событий календаря
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def authorize(user_token: str | None):

    # Если токен уже сохранён в базе данных
    if user_token:
        token_dict = json.loads(user_token)

        # Создаём объект Credentials из сохранённых данных
        return Credentials.from_authorized_user_info(
            token_dict, SCOPES
        )

    # Если токена нет — инициируем OAuth-авторизацию
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json",
        SCOPES
    )

    # Открывается локальный сервер и браузер для входа в гугл
    creds = flow.run_local_server(port=0)

    return creds


def get_upcoming_events(creds, minutes: int, calendar_id: str):

    # Получение предстоящих событий в ближайшие N минут

    service = build("calendar", "v3", credentials=creds)

    now = datetime.utcnow()
    time_max = now + timedelta(minutes=minutes)

    events = service.events().list(
        calendarId="primary",  # основной календарь пользователя
        timeMin=now.isoformat() + "Z",
        timeMax=time_max.isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    return events.get("items", [])


def get_past_events(creds, days: int = 7):

    # Получение прошедших событий за последние N дней.

    service = build("calendar", "v3", credentials=creds)

    now = datetime.utcnow()
    time_min = now - timedelta(days=days)

    events = service.events().list(
        calendarId="primary",
        timeMin=time_min.isoformat() + "Z",
        timeMax=now.isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    return events.get("items", [])


def get_calendars(creds):

    # Получение списка всех календарей пользователя.

    service = build("calendar", "v3", credentials=creds)

    calendars = service.calendarList().list().execute()
    return calendars.get("items", [])
