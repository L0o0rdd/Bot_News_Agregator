import requests
from config.config import GNEWS_API_KEY

def get_news(category: str, max_results: int = 5) -> list:
    category_map = {
        "general": "general",
        "business": "business",
        "technology": "technology",
        "entertainment": "entertainment"
    }
    url = f"https://gnews.io/api/v4/top-headlines?category={category_map.get(category, 'general')}&lang=en&max={max_results}&apikey={GNEWS_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        articles = response.json().get("articles", [])
        return [
            {
                "title": article["title"],
                "description": article["description"],
                "url": article["url"]
            }
            for article in articles
        ]
    except requests.RequestException as e:
        return [{"title": "Ошибка", "description": f"Не удалось загрузить новости: {str(e)}", "url": ""}]