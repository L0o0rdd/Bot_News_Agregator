import asyncio
from aiogram import Dispatcher, Bot
from aiogram.fsm.storage.memory import MemoryStorage
from config.config import BOT_TOKEN, ADMIN_ID
from handlers import user, admin, writer  # Убрали manager
from utils.database import init_db
from utils.logger import logger
from utils.news import start_news_fetching

async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(writer.router)  # Убрали manager.router

    await init_db()
    logger.info("Database initialized successfully.")

    # Запуск фоновой задачи для получения новостей с переводом
    asyncio.create_task(start_news_fetching(bot))
    logger.info("Started background task for fetching news with translation.")

    try:
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot polling stopped and session closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")