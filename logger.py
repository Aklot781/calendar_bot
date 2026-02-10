import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Логируем INFO и выше (WARNING, ERROR, CRITICAL)
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        # Запись логов в файл
        logging.FileHandler("bot.log", encoding="utf-8"),

        # Одновременный вывод логов в консоль
        logging.StreamHandler()
    ]
)

# Отдельный логгер для приложения
logger = logging.getLogger("calendar_bot")
