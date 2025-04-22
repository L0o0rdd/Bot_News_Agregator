import aiosqlite
from datetime import datetime
import logging
from utils.logger import logger
from config.config import RSS_FEEDS  # Исправляем импорт


async def init_db():
    async with aiosqlite.connect("news_bot.db") as db:
        logger.info("Initializing database schema...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                role TEXT DEFAULT 'user',
                view_count INTEGER DEFAULT 0,
                view_limit INTEGER DEFAULT 10,
                create_count INTEGER DEFAULT 0,
                create_limit INTEGER DEFAULT 5
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS news (
                news_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                title TEXT,
                description TEXT,
                image_url TEXT,
                writer_id INTEGER,
                source TEXT,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (writer_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_news (
                pending_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                title TEXT,
                description TEXT,
                image_url TEXT,
                writer_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (writer_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                user_id INTEGER,
                news_id INTEGER,
                rating INTEGER CHECK (rating IN (-1, 1)),
                PRIMARY KEY (user_id, news_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (news_id) REFERENCES news(news_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action_type TEXT,
                amount INTEGER,
                cost INTEGER,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                url TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER,
                category TEXT,
                PRIMARY KEY (user_id, category),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        cursor = await db.execute("SELECT COUNT(*) FROM sources")
        sources_count = (await cursor.fetchone())[0]

        if sources_count == 0:
            logger.info("Populating sources table with RSS feeds...")
            for category, feeds in RSS_FEEDS.items():
                for feed in feeds:
                    await db.execute(
                        "INSERT INTO sources (category, url, is_active) VALUES (?, ?, ?)",
                        (category, feed["url"], 1)
                    )
            await db.commit()
            logger.info("Sources table populated successfully")

        await db.commit()
        logger.info("Database schema initialized successfully")


async def get_user_role(user_id: int) -> str:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else "user"


async def set_user_role(user_id: int, role: str):
    async with aiosqlite.connect("news_bot.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, role, view_count, view_limit, create_count, create_limit) "
            "VALUES (?, ?, (SELECT view_count FROM users WHERE user_id = ?), "
            "(SELECT view_limit FROM users WHERE user_id = ?), "
            "(SELECT create_count FROM users WHERE user_id = ?), "
            "(SELECT create_limit FROM users WHERE user_id = ?))",
            (user_id, role, user_id, user_id, user_id, user_id)
        )
        await db.commit()


async def remove_user_role(user_id: int, role: str) -> bool:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        current_role = (await cursor.fetchone())[0]
        if current_role == role:
            await db.execute("UPDATE users SET role = 'user' WHERE user_id = ?", (user_id,))
            await db.commit()
            return True
        return False


async def get_users_by_role(role: str) -> list:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE role = ?", (role,))
        return [{"user_id": row[0]} for row in await cursor.fetchall()]


async def insert_pending_news(writer_id: int, title: str, description: str, image_url: str, category: str) -> int:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "INSERT INTO pending_news (category, title, description, image_url, writer_id) VALUES (?, ?, ?, ?, ?)",
            (category, title, description, image_url, writer_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_news() -> list:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT pending_id, category, title, description, image_url, writer_id, created_at FROM pending_news"
        )
        return [
            {
                "pending_id": row[0],
                "category": row[1],
                "title": row[2],
                "description": row[3],
                "image_url": row[4],
                "writer_id": row[5],
                "created_at": row[6],
            }
            for row in await cursor.fetchall()
        ]


async def approve_news(pending_id: int) -> int:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT category, title, description, image_url, writer_id FROM pending_news WHERE pending_id = ?",
            (pending_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        category, title, description, image_url, writer_id = row
        cursor = await db.execute(
            "INSERT INTO news (category, title, description, image_url, writer_id, source) VALUES (?, ?, ?, ?, ?, ?)",
            (category, title, description, image_url, writer_id, "RSS" if writer_id == 0 else "Manual")
        )
        news_id = cursor.lastrowid
        await db.execute("DELETE FROM pending_news WHERE pending_id = ?", (pending_id,))
        await db.commit()
        return news_id


async def reject_news(pending_id: int) -> int:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT writer_id FROM pending_news WHERE pending_id = ?", (pending_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        writer_id = row[0]
        await db.execute("DELETE FROM pending_news WHERE pending_id = ?", (pending_id,))
        await db.commit()
        return writer_id


async def get_news(category: str = None, limit: int = 10) -> list:
    async with aiosqlite.connect("news_bot.db") as db:
        query = "SELECT news_id, category, title, description, image_url, writer_id, source, published_at FROM news"
        params = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        query += " ORDER BY published_at DESC LIMIT ?"
        params.append(limit)
        cursor = await db.execute(query, params)
        return [
            {
                "news_id": row[0],
                "category": row[1],
                "title": row[2],
                "description": row[3],
                "image_url": row[4],
                "writer_id": row[5],
                "source": row[6],
                "published_at": row[7],
            }
            for row in await cursor.fetchall()
        ]


async def get_news_by_id(news_id: int) -> dict:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT news_id, category, title, description, image_url, writer_id, source, published_at FROM news WHERE news_id = ?",
            (news_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "news_id": row[0],
                "category": row[1],
                "title": row[2],
                "description": row[3],
                "image_url": row[4],
                "writer_id": row[5],
                "source": row[6],
                "published_at": row[7],
            }
        return None


async def set_news_rating(user_id: int, news_id: int, rating: int):
    async with aiosqlite.connect("news_bot.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO ratings (user_id, news_id, rating) VALUES (?, ?, ?)",
            (user_id, news_id, rating)
        )
        await db.commit()


async def get_news_rating(news_id: int) -> tuple[int, int]:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT rating FROM ratings WHERE news_id = ?", (news_id,)
        )
        ratings = [row[0] for row in await cursor.fetchall()]
        likes = sum(1 for r in ratings if r == 1)
        dislikes = sum(1 for r in ratings if r == -1)
        return likes, dislikes


async def get_user_rating(user_id: int, news_id: int) -> int:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT rating FROM ratings WHERE user_id = ? AND news_id = ?",
            (user_id, news_id)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def check_limit(user_id: int, action: str) -> tuple[bool, int, int]:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT view_count, view_limit, create_count, create_limit FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return False, 0, 0
        view_count, view_limit, create_count, create_limit = row
        if action == "view_news":
            return view_count < view_limit, view_count, view_limit
        elif action == "create_news":
            return create_count < create_limit, create_count, create_limit
        return False, 0, 0


async def increment_limit(user_id: int, action: str):
    async with aiosqlite.connect("news_bot.db") as db:
        if action == "view_news":
            await db.execute(
                "UPDATE users SET view_count = view_count + 1 WHERE user_id = ?",
                (user_id,)
            )
        elif action == "create_news":
            await db.execute(
                "UPDATE users SET create_count = create_count + 1 WHERE user_id = ?",
                (user_id,)
            )
        await db.commit()


async def add_limit(user_id: int, action: str, amount: int):
    async with aiosqlite.connect("news_bot.db") as db:
        if action == "view_news":
            await db.execute(
                "UPDATE users SET view_limit = view_limit + ? WHERE user_id = ?",
                (amount, user_id)
            )
        elif action == "create_news":
            await db.execute(
                "UPDATE users SET create_limit = create_limit + ? WHERE user_id = ?",
                (amount, user_id)
            )
        await db.commit()


async def add_purchase(user_id: int, action_type: str, amount: int, cost: int):
    async with aiosqlite.connect("news_bot.db") as db:
        await db.execute(
            "INSERT INTO purchases (user_id, action_type, amount, cost) VALUES (?, ?, ?, ?)",
            (user_id, action_type, amount, cost)
        )
        await db.commit()


async def get_user_stats(user_id: int) -> dict:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT role, view_count, view_limit, create_count, create_limit FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return {}
        role, view_count, view_limit, create_count, create_limit = row

        cursor = await db.execute(
            "SELECT rating FROM ratings WHERE user_id = ?", (user_id,)
        )
        ratings = [row[0] for row in await cursor.fetchall()]
        likes = sum(1 for r in ratings if r == 1)
        dislikes = sum(1 for r in ratings if r == -1)

        published_news = 0
        pending_news = 0
        average_rating = 0.0
        if role == "writer":
            cursor = await db.execute(
                "SELECT COUNT(*) FROM news WHERE writer_id = ?", (user_id,)
            )
            published_news = (await cursor.fetchone())[0]

            cursor = await db.execute(
                "SELECT COUNT(*) FROM pending_news WHERE writer_id = ?", (user_id,)
            )
            pending_news = (await cursor.fetchone())[0]

            cursor = await db.execute(
                "SELECT news_id FROM news WHERE writer_id = ?", (user_id,)
            )
            news_ids = [row[0] for row in await cursor.fetchall()]
            if news_ids:
                cursor = await db.execute(
                    "SELECT rating FROM ratings WHERE news_id IN ({})".format(
                        ",".join("?" for _ in news_ids)
                    ),
                    news_ids
                )
                ratings = [row[0] for row in await cursor.fetchall()]
                average_rating = sum(ratings) / len(ratings) if ratings else 0.0

        cursor = await db.execute(
            "SELECT action_type, amount, cost, purchase_date FROM purchases WHERE user_id = ? ORDER BY purchase_date DESC LIMIT 5",
            (user_id,)
        )
        purchases = [
            {
                "action_type": row[0],
                "amount": row[1],
                "cost": row[2],
                "purchase_date": row[3],
            }
            for row in await cursor.fetchall()
        ]

        return {
            "role": role,
            "view_count": view_count,
            "view_limit": view_limit,
            "create_count": create_count,
            "create_limit": create_limit,
            "likes": likes,
            "dislikes": dislikes,
            "published_news": published_news,
            "pending_news": pending_news,
            "average_rating": average_rating,
            "purchases": purchases,
        }


async def get_writer_news(writer_id: int) -> tuple[list, list]:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT news_id, category, title, description, image_url, writer_id FROM news WHERE writer_id = ?",
            (writer_id,)
        )
        published = [
            {
                "news_id": row[0],
                "category": row[1],
                "title": row[2],
                "description": row[3],
                "image_url": row[4],
                "writer_id": row[5] if len(row) > 5 else None,
            }
            for row in await cursor.fetchall()
        ]

        cursor = await db.execute(
            "SELECT pending_id, category, title, description, image_url FROM pending_news WHERE writer_id = ?",
            (writer_id,)
        )
        pending = [
            {
                "pending_id": row[0],
                "category": row[1],
                "title": row[2],
                "description": row[3],
                "image_url": row[4],
            }
            for row in await cursor.fetchall()
        ]

        logger.info(f"Retrieved news for writer {writer_id}: Published={len(published)}, Pending={len(pending)}")
        return published, pending


async def update_pending_news(news_id: int, title: str, description: str, image_url: str, category: str,
                              is_published: bool):
    async with aiosqlite.connect("news_bot.db") as db:
        table = "news" if is_published else "pending_news"
        id_column = "news_id" if is_published else "pending_id"
        await db.execute(
            f"UPDATE {table} SET title = ?, description = ?, image_url = ?, category = ? WHERE {id_column} = ?",
            (title, description, image_url, category, news_id)
        )
        await db.commit()


async def delete_pending_news(news_id: int, is_published: bool):
    async with aiosqlite.connect("news_bot.db") as db:
        table = "news" if is_published else "pending_news"
        id_column = "news_id" if is_published else "pending_id"
        await db.execute(f"DELETE FROM {table} WHERE {id_column} = ?", (news_id,))
        await db.commit()


async def get_sources(category: str = None) -> list:
    async with aiosqlite.connect("news_bot.db") as db:
        query = "SELECT source_id, category, url, is_active FROM sources"
        params = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        cursor = await db.execute(query, params)
        return [
            {
                "source_id": row[0],
                "category": row[1],
                "url": row[2],
                "is_active": row[3],
            }
            for row in await cursor.fetchall()
        ]


async def get_user_subscriptions(user_id: int) -> list:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT category FROM subscriptions WHERE user_id = ?", (user_id,)
        )
        return [row[0] for row in await cursor.fetchall()]


async def subscribe_to_category(user_id: int, category: str) -> bool:
    async with aiosqlite.connect("news_bot.db") as db:
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
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "DELETE FROM subscriptions WHERE user_id = ? AND category = ?",
            (user_id, category)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_subscribers(category: str) -> list:
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT user_id FROM subscriptions WHERE category = ?", (category,)
        )
        return [row[0] for row in await cursor.fetchall()]