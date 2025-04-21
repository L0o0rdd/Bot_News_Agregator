import asyncio
from aiogram import Dispatcher, Bot
from aiogram.fsm.storage.memory import MemoryStorage
from config.config import BOT_TOKEN, ADMIN_ID
from handlers import user, admin, manager, writer
from utils.database import init_db
from utils.logger import logger
from utils.rss_fether import fetch_news_task


async def main():
    # Инициализация бота
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация роутеров
    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(manager.router)
    dp.include_router(writer.router)

    # Инициализация базы данных
    await init_db()
    logger.info("Database initialized successfully.")

    # Запуск фоновой задачи для получения новостей
    asyncio.create_task(fetch_news_task(bot))
    logger.info("Started background task for fetching news.")

    try:
        # Запуск polling
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    finally:
        # Закрытие сессии бота
        await bot.session.close()
        logger.info("Bot polling stopped and session closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")