import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config.config import BOT_TOKEN
from handlers import common, admin, user, manager, writer
from utils.database import init_db

# Настройка логирования
logging.basicConfig(level=logging.INFO)

async def main():
    # Инициализация базы данных
    await init_db()

    # Инициализация бота и диспетчера с хранилищем состояний
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Подключение обработчиков
    dp.include_routers(common.router, admin.router, user.router, manager.router, writer.router)

    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())