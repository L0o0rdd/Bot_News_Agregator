import feedparser
import asyncio
from aiogram import Bot
from utils.database import get_sources, insert_pending_news, approve_news
from utils.logger import logger
from deep_translator import GoogleTranslator

async def translate_to_russian(text: str) -> str:
    try:
        translated = GoogleTranslator(source='auto', target='ru').translate(text)
        return translated if translated else text
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return text

async def fetch_news(bot: Bot):
    sources = await get_sources()
    for source in sources:
        if not source["is_active"]:
            continue
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:5]:
                news = {
                    "category": source["category"],
                    "title": entry.get("title", "Без заголовка"),
                    "description": entry.get("description", entry.get("summary", "Без описания")),
                    "image_url": "",
                    "writer_id": 0,
                    "source": source["url"],
                }
                news["title"] = await translate_to_russian(news["title"])
                news["description"] = await translate_to_russian(news["description"])
                if "enclosures" in entry:
                    for enc in entry.enclosures:
                        if enc.get("type", "").startswith("image"):
                            news["image_url"] = enc.get("href", "")
                            break
                elif "media_content" in entry:
                    for media in entry.media_content:
                        if media.get("medium", "") == "image":
                            news["image_url"] = media.get("url", "")
                            break
                pending_id = await insert_pending_news(
                    writer_id=0,
                    title=news["title"],
                    description=news["description"],
                    image_url=news["image_url"],
                    category=news["category"]
                )
                news_id = await approve_news(pending_id)
                logger.info(f"Fetched and approved RSS news: ID {pending_id} -> News ID {news_id}")
        except Exception as e:
            logger.error(f"Error fetching news from {source['url']}: {str(e)}")

async def start_news_fetching(bot: Bot):
    """Запускает периодический парсинг новостей из RSS-лент каждые 15 минут."""
    while True:
        logger.info("Starting news fetching cycle...")
        await fetch_news(bot)
        logger.info("News fetching cycle completed. Waiting for next cycle...")
        await asyncio.sleep(15 * 60)  # Ждём 15 минут перед следующим циклом