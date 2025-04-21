BOT_TOKEN = "8101651301:AAEWGYqOAY6pPnYgXNS_OyRMQ1OrMg2Q4OE"
ADMIN_ID = 925886929

# Категории новостей
CATEGORIES = ["general", "business", "technology", "entertainment", "sports"]

# RSS-ленты по категориям
RSS_FEEDS = {
    "general": [
        {"name": "ТАСС", "url": "https://tass.com/rss/v2.xml"},
        {"name": "РИА Новости", "url": "https://ria.ru/export/rss2/index.xml"},
        {"name": "The Moscow Times", "url": "https://www.themoscowtimes.com/rss/news"},
        {"name": "Коммерсантъ", "url": "https://www.kommersant.ru/RSS/main.xml"},
        {"name": "Российская Газета", "url": "https://rg.ru/xml/index.xml"},
        {"name": "Meduza", "url": "https://meduza.io/rss/all"},
    ],
    "business": [
        {"name": "Awara Group", "url": "https://awaragroup.com/feed"},
        {"name": "РБК", "url": "https://www.rbc.ru/export/rss2/economics.xml"},
        {"name": "Ведомости", "url": "https://www.vedomosti.ru/rss.xml"},
    ],
    "technology": [
        {"name": "Hi-News.ru", "url": "https://hi-news.ru/feed"},
        {"name": "RB.ru", "url": "https://rb.ru/feeds/all"},
        {"name": "Hi-Tech Mail.ru", "url": "https://hi-tech.mail.ru/rss/news"},
        {"name": "Computerra", "url": "https://computerra.ru/feed"},
        {"name": "Runet News", "url": "https://runet.news/feed.rss"},
    ],
    "entertainment": [
        {"name": "Афиша", "url": "https://www.afisha.ru/export/rss.xml"},
        {"name": "Кинопоиск", "url": "https://www.kinopoisk.ru/media/rss.xml"},
    ],
    "sports": [
        {"name": "Чемпионат", "url": "https://www.championat.com/rss.xml"},
        {"name": "Спорт-Экспресс", "url": "https://www.sport-express.ru/services/materials/news/se/"},
    ]
}