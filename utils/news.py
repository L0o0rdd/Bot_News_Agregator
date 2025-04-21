import feedparser
import asyncio
from aiogram import Bot
from utils.database import get_sources, insert_pending_news, get_pending_news, approve_news
from utils.logger import logger
from deep_translator import GoogleTranslator

async def translate_to_russian(text: str) -> str:
    """
    Переводит текст на русский язык с помощью GoogleTranslator.
    """
    try:
        translator = GoogleTranslator(source="auto", target="ru")
        translated = translator.translate(text)
        return translated if translated else text
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return text

async def fetch_news(bot: Bot):
    """
    Получает новости из активных RSS-источников, переводит их и добавляет в очередь на проверку.
    """
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
                    "description": entry.get("description", entry.get("summary", "Без описания")),
                    "image_url": "",
                    "author_id": None,
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
                # Используем insert_pending_news вместо add_pending_news
                await insert_pending_news(
                    writer_id=0,  # RSS-новости не имеют автора
                    title=news["title"],
                    description=news["description"],
                    image_url=news["image_url"],
                    category=news["category"]
                )
                # Автоматически одобряем новость
                pending_news = await get_pending_news()
                if pending_news:
                    pending_id = pending_news[-1]["pending_id"]  # Берем последнюю добавленную новость
                    await approve_news(pending_id)
                    logger.info(f"Automatically approved RSS news ID {pending_id}")
                logger.info(f"Fetched and translated news: {news['title']}")
        except Exception as e:
            logger.error(f"Error fetching news from {source['url']}: {str(e)}")

async def start_news_fetching(bot: Bot):
    """
    Запускает бесконечный цикл для периодического получения новостей из RSS-лент.
    """
    while True:
        logger.info("Fetching news from RSS sources...")
        await fetch_news(bot)
        await asyncio.sleep(3600)  # Проверяем каждый час