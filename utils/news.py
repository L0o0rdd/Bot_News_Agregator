import feedparser
from config.config import RSS_FEEDS


def get_news(category: str, max_results: int = 5) -> list:
    feeds = RSS_FEEDS.get(category, [])
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

    return articles[:max_results]