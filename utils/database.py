import aiosqlite
import asyncio
from datetime import datetime

DB_NAME = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL
            )
        """)
        # Таблица новостей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS news (
                news_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                image_url TEXT,
                author_id INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                is_active BOOLEAN NOT NULL
            )
        """)
        # Таблица ожидающих новостей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_news (
                pending_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                image_url TEXT,
                author_id INTEGER NOT NULL,
                submitted_at DATETIME NOT NULL
            )
        """)
        # Добавляем админа по умолчанию
        await db.execute("INSERT OR IGNORE INTO users (user_id, role) VALUES (?, ?)", (925886929, "admin"))
        await db.commit()

async def get_user_role(user_id: int) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else "user"

async def set_user_role(user_id: int, role: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO users (user_id, role) VALUES (?, ?)", (user_id, role))
        await db.commit()

async def remove_user_role(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_users_by_role(role: str) -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE role = ?", (role,))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def submit_news(category: str, title: str, description: str, author_id: int, image_url: str = None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO pending_news (category, title, description, image_url, author_id, submitted_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (category, title, description, image_url, author_id, datetime.utcnow())
        )
        await db.commit()

async def update_pending_news(pending_id: int, category: str, title: str, description: str, image_url: str = None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE pending_news SET category = ?, title = ?, description = ?, image_url = ? WHERE pending_id = ?",
            (category, title, description, image_url, pending_id)
        )
        await db.commit()

async def get_pending_news() -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM pending_news")
        rows = await cursor.fetchall()
        return [
            {
                "pending_id": row[0],
                "category": row[1],
                "title": row[2],
                "description": row[3],
                "image_url": row[4],
                "author_id": row[5],
                "submitted_at": row[6]
            }
            for row in rows
        ]

async def get_pending_news_by_author(author_id: int) -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM pending_news WHERE author_id = ?", (author_id,))
        rows = await cursor.fetchall()
        return [
            {
                "pending_id": row[0],
                "category": row[1],
                "title": row[2],
                "description": row[3],
                "image_url": row[4],
                "author_id": row[5],
                "submitted_at": row[6]
            }
            for row in rows
        ]

async def approve_news(pending_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM pending_news WHERE pending_id = ?", (pending_id,))
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "INSERT INTO news (category, title, description, image_url, author_id, created_at, is_active) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (row[1], row[2], row[3], row[4], row[5], datetime.utcnow(), 1)
            )
            await db.execute("DELETE FROM pending_news WHERE pending_id = ?", (pending_id,))
            await db.commit()
            return row[5]  # Возвращаем author_id
        return None

async def reject_news(pending_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT author_id FROM pending_news WHERE pending_id = ?", (pending_id,))
        row = await cursor.fetchone()
        await db.execute("DELETE FROM pending_news WHERE pending_id = ?", (pending_id,))
        await db.commit()
        return row[0] if row else None

async def get_news(category: str, active: bool = True, limit: int = 5, offset: int = 0) -> list:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT news_id, category, title, description, image_url, author_id, created_at "
            "FROM news WHERE category = ? AND is_active = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (category, 1 if active else 0, limit, offset)
        )
        rows = await cursor.fetchall()
        return [
            {
                "news_id": row[0],
                "category": row[1],
                "title": row[2],
                "description": row[3],
                "image_url": row[4],
                "author_id": row[5],
                "created_at": row[6]
            }
            for row in rows
        ]

async def get_news_count(category: str, active: bool = True) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM news WHERE category = ? AND is_active = ?",
            (category, 1 if active else 0)
        )
        row = await cursor.fetchone()
        return row[0]

async def clear_old_news(days: int = 30):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE news SET is_active = 0 WHERE created_at < datetime('now', ?)",
            (f"-{days} days",)
        )
        await db.commit()