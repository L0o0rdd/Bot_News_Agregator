import feedparser
from cachetools import TTLCache
from config.config import RSS_FEEDS

# Кэш на 10 минут (600 секунд)
cache = TTLCache(maxsize=100, ttl=600)


def get_news(category: str, source: str = None, max_results: int = 5) -> list:
    feeds = RSS_FEEDS.get(category, [])
    if source:
        feeds = [feed for feed in feeds if feed["name"] == source]

    cache_key = f"{category}_{source or 'all'}"
    if cache_key in cache:
        return cache[cache_key]

    articles = []
    for feed in feeds:
        try:
            parsed_feed = feedparser.parse(feed["url"])
            for entry in parsed_feed.entries[:max_results]:
                articles.append({
                    "title": entry.get("title", "Без заголовка"),
                    "description": entry.get("summary", "Описание отсутствует"),
                    "url": entry.get("link", ""),
                    "source": feed["name"]
                })
        except Exception as e:
            articles.append({
                "title": "Ошибка",
                "description": f"Не удалось загрузить новости из {feed['name']}: {str(e)}",
                "url": "",
                "source": feed["name"]
            })

    articles = articles[:max_results]
    cache[cache_key] = articles
    return articles