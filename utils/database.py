import aiosqlite
import asyncio
from utils.logger import logger

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
                rating INTEGER,  -- 1 для лайка, -1 для дизлайка
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
        await db.commit()


async def set_user_role(user_id: int, role: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, role) VALUES (?, ?)",
            (user_id, role)
        )
        await db.execute(
            "INSERT INTO action_logs (user_id, action_type, target_id, details) VALUES (?, ?, ?, ?)",
            (user_id, "assign_role", user_id, f"Assigned role {role}")
        )
        await db.commit()
        logger.info(f"Set role {role} for user {user_id}")


async def get_user_role(user_id: int) -> str:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT role FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "user"


async def remove_user_role(user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "UPDATE users SET role = 'user' WHERE user_id = ?", (user_id,)
        )
        await db.execute(
            "INSERT INTO action_logs (user_id, action_type, target_id, details) VALUES (?, ?, ?, ?)",
            (user_id, "remove_role", user_id, "Removed role")
        )
        await db.commit()
        logger.info(f"Removed role from user {user_id}")


async def get_users_by_role(role: str) -> list:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT user_id FROM users WHERE role = ?", (role,)
        ) as cursor:
            return [row[0] for row in await cursor.fetchall()]


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
                news.get("source", "User submission"),
            ),
        )
        await db.commit()
        logger.info(f"Added pending news by user {news['author_id']}: {news['title']}")


async def get_pending_news() -> list:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT * FROM pending_news ORDER BY submitted_at ASC"
        ) as cursor:
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in await cursor.fetchall()]


async def approve_news(pending_id: int) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT * FROM pending_news WHERE pending_id = ?", (pending_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
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
                await db.execute(
                    "DELETE FROM pending_news WHERE pending_id = ?", (pending_id,)
                )
                await db.execute(
                    "INSERT INTO action_logs (user_id, action_type, target_id, details) VALUES (?, ?, ?, ?)",
                    (news["author_id"], "approve_news", pending_id, "Approved news")
                )
                await db.commit()
                logger.info(f"Approved news ID {pending_id}")
                return news["author_id"]
    return None


async def reject_news(pending_id: int) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT author_id FROM pending_news WHERE pending_id = ?", (pending_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                author_id = row[0]
                await db.execute(
                    "DELETE FROM pending_news WHERE pending_id = ?", (pending_id,)
                )
                await db.execute(
                    "INSERT INTO action_logs (user_id, action_type, target_id, details) VALUES (?, ?, ?, ?)",
                    (author_id, "reject_news", pending_id, "Rejected news")
                )
                await db.commit()
                logger.info(f"Rejected news ID {pending_id}")
                return author_id
    return None


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
        async with db.execute(
                "SELECT * FROM news WHERE news_id = ?", (news_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
    return None


async def add_source(url: str, category: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT OR IGNORE INTO sources (url, category) VALUES (?, ?)",
            (url, category),
        )
        await db.commit()
        logger.info(f"Added source {url} with category {category}")


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


async def toggle_source(source_id: int) -> bool:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT is_active FROM sources WHERE source_id = ?", (source_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                new_status = 0 if row[0] == 1 else 1
                await db.execute(
                    "UPDATE sources SET is_active = ? WHERE source_id = ?",
                    (new_status, source_id)
                )
                await db.commit()
                logger.info(f"Toggled source ID {source_id} to is_active={new_status}")
                return True
    return False


async def clear_old_news(days: int = 30):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            """
            DELETE FROM news
            WHERE published_at < datetime('now', '-' || ? || ' days')
            """,
            (days,),
        )
        await db.commit()
        logger.info(f"Cleared news older than {days} days.")


async def set_news_rating(user_id: int, news_id: int, rating: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO news_ratings (user_id, news_id, rating)
            VALUES (?, ?, ?)
            """,
            (user_id, news_id, rating),
        )
        await db.commit()
        logger.info(f"User {user_id} set rating {rating} for news ID {news_id}")


async def get_news_rating(news_id: int) -> tuple:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT COUNT(*) FROM news_ratings WHERE news_id = ? AND rating = 1",
                (news_id,),
        ) as cursor:
            likes = (await cursor.fetchone())[0]
        async with db.execute(
                "SELECT COUNT(*) FROM news_ratings WHERE news_id = ? AND rating = -1",
                (news_id,),
        ) as cursor:
            dislikes = (await cursor.fetchone())[0]
        return likes, dislikes


async def get_user_rating(user_id: int, news_id: int) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT rating FROM news_ratings WHERE user_id = ? AND news_id = ?",
                (user_id, news_id),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_admin_stats() -> dict:
    stats = {}
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            stats["total_users"] = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE role = 'manager'") as cursor:
            stats["managers"] = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE role = 'writer'") as cursor:
            stats["writers"] = (await cursor.fetchone())[0]
        async with db.execute("SELECT category, COUNT(*) FROM news GROUP BY category") as cursor:
            stats["news_by_category"] = dict(await cursor.fetchall())
        async with db.execute("SELECT COUNT(*) FROM news_ratings WHERE rating = 1") as cursor:
            stats["total_likes"] = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM news_ratings WHERE rating = -1") as cursor:
            stats["total_dislikes"] = (await cursor.fetchone())[0]
        async with db.execute("""
            SELECT news_id, 
                   (SELECT COUNT(*) FROM news_ratings nr WHERE nr.news_id = n.news_id AND nr.rating = 1) -
                   (SELECT COUNT(*) FROM news_ratings nr WHERE nr.news_id = n.news_id AND nr.rating = -1) as rating,
                   title
            FROM news n
            ORDER BY rating DESC LIMIT 5
        """) as cursor:
            stats["top_news"] = [{"news_id": row[0], "rating": row[1], "title": row[2]} for row in
                                 await cursor.fetchall()]
    return stats


async def get_user_stats(user_id: int) -> dict:
    stats = {}
    async with aiosqlite.connect(DATABASE) as db:
        stats["role"] = await get_user_role(user_id)
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
        async with db.execute("""
            SELECT n.news_id, n.title
            FROM news_ratings nr
            JOIN news n ON nr.news_id = n.news_id
            WHERE nr.user_id = ? AND nr.rating = 1
            LIMIT 3
        """, (user_id,)) as cursor:
            stats["liked_news"] = [{"news_id": row[0], "title": row[1]} for row in await cursor.fetchall()]

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
            async with db.execute("""
                SELECT n.news_id
                FROM news n
                WHERE n.author_id = ?
            """, (user_id,)) as cursor:
                news_ids = [row[0] for row in await cursor.fetchall()]
                total_rating = 0
                for news_id in news_ids:
                    likes, dislikes = await get_news_rating(news_id)
                    total_rating += (likes - dislikes)
                stats["average_rating"] = total_rating / len(news_ids) if news_ids else 0

        if stats["role"] == "manager":
            async with db.execute(
                    "SELECT COUNT(*) FROM action_logs WHERE user_id = ? AND action_type = 'approve_news'",
                    (user_id,)
            ) as cursor:
                stats["approved_news"] = (await cursor.fetchone())[0]
            async with db.execute(
                    "SELECT COUNT(*) FROM action_logs WHERE user_id = ? AND action_type = 'reject_news'",
                    (user_id,)
            ) as cursor:
                stats["rejected_news"] = (await cursor.fetchone())[0]

        if stats["role"] == "admin":
            async with db.execute(
                    "SELECT COUNT(*) FROM action_logs WHERE user_id = ? AND action_type = 'assign_role'",
                    (user_id,)
            ) as cursor:
                stats["roles_assigned"] = (await cursor.fetchone())[0]
            async with db.execute(
                    "SELECT COUNT(*) FROM action_logs WHERE user_id = ? AND action_type = 'remove_role'",
                    (user_id,)
            ) as cursor:
                stats["roles_removed"] = (await cursor.fetchone())[0]
            stats["general_stats"] = await get_admin_stats()

    return stats


async def get_writer_news(user_id: int) -> tuple:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT news_id, category, title FROM news WHERE author_id = ?",
                (user_id,)
        ) as cursor:
            columns = [desc[0] for desc in cursor.description]
            published = [dict(zip(columns, row)) for row in await cursor.fetchall()]
        async with db.execute(
                "SELECT pending_id, category, title FROM pending_news WHERE author_id = ?",
                (user_id,)
        ) as cursor:
            columns = [desc[0] for desc in cursor.description]
            pending = [dict(zip(columns, row)) for row in await cursor.fetchall()]
    return published, pending


async def update_news(news_id: int, news: dict):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            """
            UPDATE news
            SET category = ?, title = ?, description = ?, image_url = ?
            WHERE news_id = ?
            """,
            (
                news["category"],
                news["title"],
                news["description"],
                news["image_url"],
                news_id,
            ),
        )
        await db.commit()
        logger.info(f"Updated news ID {news_id}")


async def update_pending_news(pending_id: int, news: dict):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            """
            UPDATE pending_news
            SET category = ?, title = ?, description = ?, image_url = ?
            WHERE pending_id = ?
            """,
            (
                news["category"],
                news["title"],
                news["description"],
                news["image_url"],
                pending_id,
            ),
        )
        await db.commit()
        logger.info(f"Updated pending news ID {pending_id}")


async def subscribe_to_category(user_id: int, category: str) -> bool:
    async with aiosqlite.connect(DATABASE) as db:
        try:
            await db.execute(
                "INSERT INTO subscriptions (user_id, category) VALUES (?, ?)",
                (user_id, category),
            )
            await db.commit()
            logger.info(f"User {user_id} subscribed to category {category}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe user {user_id} to category {category}: {str(e)}")
            return False


async def unsubscribe_from_category(user_id: int, category: str) -> bool:
    async with aiosqlite.connect(DATABASE) as db:
        try:
            await db.execute(
                "DELETE FROM subscriptions WHERE user_id = ? AND category = ?",
                (user_id, category),
            )
            await db.commit()
            logger.info(f"User {user_id} unsubscribed from category {category}")
            return True
        except Exception as e:
            logger.error(f"Failed to unsubscribe user {user_id} from category {category}: {str(e)}")
            return False


async def get_user_subscriptions(user_id: int) -> list:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT category FROM subscriptions WHERE user_id = ?",
                (user_id,)
        ) as cursor:
            return [row[0] for row in await cursor.fetchall()]


async def get_subscribers(category: str) -> list:
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
                "SELECT user_id FROM subscriptions WHERE category = ?",
                (category,)
        ) as cursor:
            return [row[0] for row in await cursor.fetchall()]