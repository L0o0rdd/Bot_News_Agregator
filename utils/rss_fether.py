import asyncio
import feedparser
from utils.database import get_sources, add_pending_news, get_subscribers
from utils.logger import logger


async def fetch_news_task(bot):
    while True:
        logger.info("Fetching news from RSS sources...")
        sources = await get_sources()
        for source in sources:
            if not source["is_active"]:
                continue
            try:
                feed = feedparser.parse(source["url"])
                for entry in feed.entries[:5]:  # Ограничим до 5 новостей с каждого источника
                    news = {
                        "category": source["category"],
                        "title": entry.get("title", "Без заголовка"),
                        "description": entry.get("summary", "Без описания"),
                        "image_url": entry.get("media_content", [{}])[0].get("url", ""),
                        "author_id": 0,  # RSS-новости не имеют автора
                        "source": source["url"]
                    }
                    await add_pending_news(news)
                    logger.info(f"Added RSS news: {news['title']}")
            except Exception as e:
                logger.error(f"Error fetching RSS from {source['url']}: {str(e)}")

        # Уведомление подписчиков (опционально, если новости сразу публикуются)
        # Здесь можно добавить логику уведомления, если новости публикуются автоматически

        await asyncio.sleep(300)  # Проверяем каждые 5 минут