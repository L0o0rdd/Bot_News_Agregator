import asyncio
import feedparser
from aiogram import Bot
from utils.database import get_sources, insert_pending_news, get_subscribers
from utils.logger import logger

async def fetch_news_task(bot: Bot):
    """
    Периодически получает новости из активных RSS-источников, добавляет их в очередь на проверку
    и уведомляет подписчиков.
    """
    while True:
        logger.info("Fetching news from RSS sources...")
        sources = await get_sources()
        for source in sources:
            if not source["is_active"]:
                continue
            try:
                feed = feedparser.parse(source["url"])
                for entry in feed.entries[:5]:  # Ограничиваем до 5 новостей на источник
                    news = {
                        "category": source["category"],
                        "title": entry.get("title", "Без заголовка"),
                        "description": entry.get("summary", "Без описания"),
                        "image_url": entry.get("media_content", [{}])[0].get("url", ""),
                        "author_id": 0,  # RSS-новости не имеют автора
                        "source": source["url"]
                    }
                    # Добавляем новость в очередь на проверку
                    await insert_pending_news(
                        writer_id=0,
                        title=news["title"],
                        description=news["description"],
                        image_url=news["image_url"],
                        category=news["category"]
                    )
                    logger.info(f"Added RSS news: {news['title']}")
                    # Уведомляем подписчиков категории
                    subscribers = await get_subscribers(news["category"])
                    for user_id in subscribers:
                        try:
                            await bot.send_message(
                                chat_id=user_id,
                                text=f"📰 Новая новость в категории {news['category']}!\n\n"
                                     f"**{news['title']}**\n{news['description'][:200]}..."
                            )
                            logger.info(f"Notified user {user_id} about new RSS news: {news['title']}")
                        except Exception as e:
                            logger.error(f"Failed to notify user {user_id}: {str(e)}")
            except Exception as e:
                logger.error(f"Error fetching RSS from {source['url']}: {str(e)}")

        await asyncio.sleep(300)  # Проверяем каждые 5 минут