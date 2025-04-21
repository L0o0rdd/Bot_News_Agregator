import aiosqlite
import asyncio
from datetime import datetime, timedelta
from utils.logger import logger
from config.config import RSS_FEEDS, ADMIN_ID

DATABASE = "news_bot.db"


async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                role TEXT DEFAULT 'user'
            )
        """)
        # Таблица новостей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS news (
                news_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                title TEXT,
                description TEXT,
                image_url TEXT,
                author_id INTEGER,
                source TEXT,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблица ожидающих новостей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_news (
                pending_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                title TEXT,
                description TEXT,
                image_url TEXT,
                author_id INTEGER,
                source TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблица источников
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                category TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        # Таблица рейтингов новостей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS news_ratings (
                user_id INTEGER,
                news_id INTEGER,
                rating INTEGER,
                PRIMARY KEY (user_id, news_id)
            )
        """)
        # Таблица логов действий
        await db.execute("""
            CREATE TABLE IF NOT EXISTS action_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action_type TEXT,
                target_id INTEGER,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблица подписок
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER,
                category TEXT,
                PRIMARY KEY (user_id, category)
            )
        """)
        # Таблица лимитов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS limits (
                user_id INTEGER,
                action_type TEXT,  -- 'view_news' или 'create_news'
                count INTEGER DEFAULT 0,
                last_reset TIMESTAMP,
                total_limit INTEGER,
                PRIMARY KEY (user_id, action_type)
            )
        """)
        # Таблица покупок
        await db.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action_type TEXT,
                amount INTEGER,
                cost INTEGER,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

        # Добавляем админа
        role = await get_user_role(ADMIN_ID)
        if role != "admin":
            await set_user_role(ADMIN_ID, "admin")
            logger.info(f"Admin with ID {ADMIN_ID} added to database with role 'admin' 🌟")

        # Добавляем RSS-ленты
        for category, feeds in RSS_FEEDS.items():
            for feed in feeds:
                url = feed["url"]
                await add_source(url, category)
                logger.info(f"Added RSS feed {url} for category {category} 🌐")


async def get_user_role(user_id: int) -> str:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "user"


async def set_user_role(user_id: int, role: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("INSERT OR REPLACE INTO users (user_id, role) VALUES (?, ?)", (user_id, role))
        await db.commit()


async def add_source(url: str, category: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("INSERT OR IGNORE INTO sources (url, category) VALUES (?, ?)", (url, category))
        await db.commit()


async def get_sources(category: str = None) -> list:
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT * FROM sources"
        params = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        async with db.execute(query, params) as cursor:
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in await cursor.fetchall()]


# Функции для работы с лимитами
async def reset_limits_if_needed(user_id: int, action_type: str):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT last_reset, total_limit FROM limits WHERE user_id = ? AND action_type = ?",
                (user_id, action_type)
        ) as cursor:
            row = await cursor.fetchone()
            default_limit = 10 if action_type == "view_news" else 2  # 10 для просмотров, 2 для постов
            now = datetime.utcnow()
            if not row:
                await db.execute(
                    "INSERT INTO limits (user_id, action_type, count, last_reset, total_limit) VALUES (?, ?, ?, ?, ?)",
                    (user_id, action_type, 0, now, default_limit)
                )
                await db.commit()
                return default_limit
            last_reset, total_limit = row[0], row[1]
            last_reset = datetime.fromisoformat(last_reset) if last_reset else now
            if (now - last_reset).days >= 1:
                await db.execute(
                    "UPDATE limits SET count = 0, last_reset = ? WHERE user_id = ? AND action_type = ?",
                    (now, user_id, action_type)
                )
                await db.commit()
            return total_limit


async def check_limit(user_id: int, action_type: str) -> tuple[bool, int, int]:
    total_limit = await reset_limits_if_needed(user_id, action_type)
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT count FROM limits WHERE user_id = ? AND action_type = ?",
                (user_id, action_type)
        ) as cursor:
            row = await cursor.fetchone()
            current_count = row[0] if row else 0
            return current_count < total_limit, current_count, total_limit


async def increment_limit(user_id: int, action_type: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "UPDATE limits SET count = count + 1 WHERE user_id = ? AND action_type = ?",
            (user_id, action_type)
        )
        await db.commit()


async def add_limit(user_id: int, action_type: str, amount: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "UPDATE limits SET total_limit = total_limit + ? WHERE user_id = ? AND action_type = ?",
            (amount, user_id, action_type)
        )
        await db.commit()


async def add_purchase(user_id: int, action_type: str, amount: int, cost: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT INTO purchases (user_id, action_type, amount, cost) VALUES (?, ?, ?, ?)",
            (user_id, action_type, amount, cost)
        )
        await db.commit()


async def get_user_stats(user_id: int) -> dict:
    async with aiosqlite.connect(DATABASE) as db:
        stats = {"role": await get_user_role(user_id)}

        # Статистика просмотров и постов
        view_allowed, view_count, view_limit = await check_limit(user_id, "view_news")
        stats["view_count"] = view_count
        stats["view_limit"] = view_limit

        if stats["role"] == "writer":
            create_allowed, create_count, create_limit = await check_limit(user_id, "create_news")
            stats["create_count"] = create_count
            stats["create_limit"] = create_limit

        # История покупок
        async with db.execute(
                "SELECT action_type, amount, cost, purchase_date FROM purchases WHERE user_id = ? ORDER BY purchase_date DESC LIMIT 5",
                (user_id,)
        ) as cursor:
            columns = [desc[0] for desc in cursor.description]
            stats["purchases"] = [dict(zip(columns, row)) for row in await cursor.fetchall()]

        # Остальная статистика
        async with db.execute(
                "SELECT COUNT(*) FROM news_ratings WHERE user_id = ? AND rating = 1",
                (user_id,)
        ) as cursor:
            stats["likes"] = (await cursor.fetchone())[0]
        async with db.execute(
                "SELECT COUNT(*) FROM news_ratings WHERE user_id = ? AND rating = -1",
                (user_id,)
        ) as cursor:
            stats["dislikes"] = (await cursor.fetchone())[0]

        if stats["role"] == "writer":
            async with db.execute(
                    "SELECT COUNT(*) FROM news WHERE author_id = ?",
                    (user_id,)
            ) as cursor:
                stats["published_news"] = (await cursor.fetchone())[0]
            async with db.execute(
                    "SELECT COUNT(*) FROM pending_news WHERE author_id = ?",
                    (user_id,)
            ) as cursor:
                stats["pending_news"] = (await cursor.fetchone())[0]
            async with db.execute(
                    "SELECT AVG(rating) FROM news_ratings WHERE news_id IN (SELECT news_id FROM news WHERE author_id = ?)",
                    (user_id,)
            ) as cursor:
                avg_rating = (await cursor.fetchone())[0]
                stats["average_rating"] = avg_rating if avg_rating else 0

        return stats


# Остальные функции (без изменений)
async def add_pending_news(news: dict):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            """
            INSERT INTO pending_news (category, title, description, image_url, author_id, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                news["category"],
                news["title"],
                news["description"],
                news["image_url"],
                news["author_id"],
                news["source"],
            ),
        )
        await db.commit()


async def get_pending_news() -> list:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT * FROM pending_news") as cursor:
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in await cursor.fetchall()]


async def get_news(category: str = None, limit: int = 10) -> list:
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT * FROM news"
        params = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        query += " ORDER BY published_at DESC LIMIT ?"
        params.append(limit)
        async with db.execute(query, params) as cursor:
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in await cursor.fetchall()]


async def get_news_by_id(news_id: int) -> dict:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT * FROM news WHERE news_id = ?", (news_id,)) as cursor:
            columns = [desc[0] for desc in cursor.description]
            row = await cursor.fetchone()
            return dict(zip(columns, row)) if row else None


async def approve_news(pending_id: int) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT * FROM pending_news WHERE pending_id = ?", (pending_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            columns = [desc[0] for desc in cursor.description]
            news = dict(zip(columns, row))

        await db.execute(
            """
            INSERT INTO news (category, title, description, image_url, author_id, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                news["category"],
                news["title"],
                news["description"],
                news["image_url"],
                news["author_id"],
                news["source"],
            ),
        )
        await db.execute("DELETE FROM pending_news WHERE pending_id = ?", (pending_id,))
        await db.commit()
        return news["author_id"]


async def reject_news(pending_id: int) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT author_id FROM pending_news WHERE pending_id = ?", (pending_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            author_id = row[0]
        await db.execute("DELETE FROM pending_news WHERE pending_id = ?", (pending_id,))
        await db.commit()
        return author_id


async def set_news_rating(user_id: int, news_id: int, rating: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO news_ratings (user_id, news_id, rating) VALUES (?, ?, ?)",
            (user_id, news_id, rating),
        )
        await db.commit()


async def get_news_rating(news_id: int) -> tuple[int, int]:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT COUNT(*) FROM news_ratings WHERE news_id = ? AND rating = 1",
                (news_id,)
        ) as cursor:
            likes = (await cursor.fetchone())[0]
        async with db.execute(
                "SELECT COUNT(*) FROM news_ratings WHERE news_id = ? AND rating = -1",
                (news_id,)
        ) as cursor:
            dislikes = (await cursor.fetchone())[0]
        return likes, dislikes


async def get_user_rating(user_id: int, news_id: int) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT rating FROM news_ratings WHERE user_id = ? AND news_id = ?",
                (user_id, news_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def toggle_source(source_id: int) -> bool:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT is_active FROM sources WHERE source_id = ?", (source_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            is_active = row[0]
        new_status = 0 if is_active else 1
        await db.execute(
            "UPDATE sources SET is_active = ? WHERE source_id = ?",
            (new_status, source_id)
        )
        await db.commit()
        return True


async def remove_user_role(user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "UPDATE users SET role = 'user' WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def get_users_by_role(role: str) -> list:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT user_id FROM users WHERE role = ?",
                (role,)
        ) as cursor:
            return [row[0] for row in await cursor.fetchall()]


async def get_subscribers(category: str) -> list:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT user_id FROM subscriptions WHERE category = ?",
                (category,)
        ) as cursor:
            return [row[0] for row in await cursor.fetchall()]


async def get_user_subscriptions(user_id: int) -> list:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT category FROM subscriptions WHERE user_id = ?",
                (user_id,)
        ) as cursor:
            return [row[0] for row in await cursor.fetchall()]


async def subscribe_to_category(user_id: int, category: str) -> bool:
    async with aiosqlite.connect(DATABASE) as db:
        try:
            await db.execute(
                "INSERT INTO subscriptions (user_id, category) VALUES (?, ?)",
                (user_id, category)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def unsubscribe_from_category(user_id: int, category: str) -> bool:
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "DELETE FROM subscriptions WHERE user_id = ? AND category = ?",
            (user_id, category)
        )
        await db.commit()
        return True


async def update_news(news_id: int, news: dict):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            """
            UPDATE news
            SET category = ?, title = ?, description = ?, image_url = ?
            WHERE news_id = ?
            """,
            (news["category"], news["title"], news["description"], news["image_url"], news_id),
        )
        await db.commit()


async def update_pending_news(pending_id: int, news: dict):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            """
            UPDATE pending_news
            SET category = ?, title = ?, description = ?, image_url = ?
            WHERE pending_id = ?
            """,
            (news["category"], news["title"], news["description"], news["image_url"], pending_id),
        )
        await db.commit()


async def get_writer_news(user_id: int) -> tuple[list, list]:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT * FROM news WHERE author_id = ?",
                (user_id,)
        ) as cursor:
            columns = [desc[0] for desc in cursor.description]
            published = [dict(zip(columns, row)) for row in await cursor.fetchall()]
        async with db.execute(
                "SELECT * FROM pending_news WHERE author_id = ?",
                (user_id,)
        ) as cursor:
            columns = [desc[0] for desc in cursor.description]
            pending = [dict(zip(columns, row)) for row in await cursor.fetchall()]
        return published, pending


async def clear_old_news(days: int):
    async with aiosqlite.connect(DATABASE) as db:
        threshold = (datetime.utcnow() - timedelta(days=days)).isoformat()
        await db.execute("DELETE FROM news WHERE published_at < ?", (threshold,))
        await db.execute("DELETE FROM pending_news WHERE submitted_at < ?", (threshold,))
        await db.commit()


async def get_admin_stats() -> dict:
    async with aiosqlite.connect(DATABASE) as db:
        stats = {}
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            stats["total_users"] = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE role = 'manager'") as cursor:
            stats["managers"] = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE role = 'writer'") as cursor:
            stats["writers"] = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM news_ratings WHERE rating = 1") as cursor:
            stats["total_likes"] = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM news_ratings WHERE rating = -1") as cursor:
            stats["total_dislikes"] = (await cursor.fetchone())[0]

        stats["news_by_category"] = {}
        async with db.execute("SELECT category, COUNT(*) FROM news GROUP BY category") as cursor:
            for row in await cursor.fetchall():
                stats["news_by_category"][row[0]] = row[1]

        stats["top_news"] = []
        async with db.execute(
                """
                SELECT news_id, title, (SELECT COUNT(*) FROM news_ratings WHERE news_id = news.news_id AND rating = 1) -
                (SELECT COUNT(*) FROM news_ratings WHERE news_id = news.news_id AND rating = -1) as rating
                FROM news
                ORDER BY rating DESC
                LIMIT 5
                """
        ) as cursor:
            columns = [desc[0] for desc in cursor.description]
            stats["top_news"] = [dict(zip(columns, row)) for row in await cursor.fetchall()]

        return stats