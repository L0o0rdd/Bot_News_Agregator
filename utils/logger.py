import logging
from logging.handlers import RotatingFileHandler
import os

# Настройка логирования
def setup_logger():
    logger = logging.getLogger("NewsBot")
    logger.setLevel(logging.INFO)

    # Создаём директорию для логов, если её нет
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Ротация логов: максимум 5 МБ, храним до 5 резервных копий
    handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "bot.log"),
        maxBytes=5 * 1024 * 1024,  # 5 МБ
        backupCount=5
    )
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Также выводим логи в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# Инициализируем логгер
logger = setup_logger()