import feedparser
import asyncio
from aiogram import Bot
from utils.database import get_sources, add_pending_news
from utils.logger import logger
from deep_translator import GoogleTranslator

# Функция перевода текста на русский
async def translate_to_russian(text: str) -> str:
    try:
        translator = GoogleTranslator(source="auto", target="ru")
        translated = translator.translate(text)
        return translated if translated else text
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return text  # Возвращаем оригинальный текст в случае ошибки

async def fetch_news(bot: Bot):
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
                    "description": entry.get("description", entry.get("summary", "Без описания")),
                    "image_url": "",
                    "author_id": None,
                    "source": source["url"],
                }
                # Переводим заголовок и описание на русский
                news["title"] = await translate_to_russian(news["title"])
                news["description"] = await translate_to_russian(news["description"])
                # Ищем изображение в enclosures или media_content
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
                await add_pending_news(news)
                logger.info(f"Fetched and translated news: {news['title']}")
        except Exception as e:
            logger.error(f"Error fetching news from {source['url']}: {str(e)}")

async def start_news_fetching(bot: Bot):
    while True:
        logger.info("Fetching news from RSS sources...")
        await fetch_news(bot)
        await asyncio.sleep(3600)  # Обновление каждый час