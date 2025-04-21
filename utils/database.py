import aiosqlite
from datetime import datetime
from utils.logger import logger  # Импортируем логгер

# Инициализация базы данных
async def init_db():
    """
    Создаёт таблицы в базе данных и обновляет схему, если необходимо.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        logger.info("Initializing database schema...")
        # Создание таблицы users
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                role TEXT DEFAULT 'user'
            )
        """)
        # Проверка и добавление недостающих столбцов в таблице users
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "view_count" not in columns:
            logger.info("Adding view_count column to users table")
            await db.execute("ALTER TABLE users ADD COLUMN view_count INTEGER DEFAULT 0")
        if "view_limit" not in columns:
            logger.info("Adding view_limit column to users table")
            await db.execute("ALTER TABLE users ADD COLUMN view_limit INTEGER DEFAULT 10")
        if "create_count" not in columns:
            logger.info("Adding create_count column to users table")
            await db.execute("ALTER TABLE users ADD COLUMN create_count INTEGER DEFAULT 0")
        if "create_limit" not in columns:
            logger.info("Adding create_limit column to users table")
            await db.execute("ALTER TABLE users ADD COLUMN create_limit INTEGER DEFAULT 5")

        # Создание таблицы news
        await db.execute("""
            CREATE TABLE IF NOT EXISTS news (
                news_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                title TEXT,
                description TEXT,
                image_url TEXT,
                source TEXT,
                published_at TEXT
            )
        """)
        # Проверка и добавление недостающего столбца writer_id в таблице news
        cursor = await db.execute("PRAGMA table_info(news)")
        news_columns = [row[1] for row in await cursor.fetchall()]
        if "writer_id" not in news_columns:
            logger.info("Adding writer_id column to news table")
            await db.execute("ALTER TABLE news ADD COLUMN writer_id INTEGER")
        else:
            logger.info("writer_id column already exists in news table")

        # Таблица новостей на проверке
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_news (
                pending_id INTEGER PRIMARY KEY AUTOINCREMENT,
                writer_id INTEGER,
                title TEXT,
                description TEXT,
                image_url TEXT,
                category TEXT,
                created_at TEXT
            )
        """)
        # Таблица рейтингов новостей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                user_id INTEGER,
                news_id INTEGER,
                rating INTEGER,
                PRIMARY KEY (user_id, news_id)
            )
        """)
        # Таблица источников RSS
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                url TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        # Таблица подписок пользователей на категории
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER,
                category TEXT,
                PRIMARY KEY (user_id, category)
            )
        """)
        # Таблица покупок лимитов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action_type TEXT,
                amount INTEGER,
                cost INTEGER,
                purchase_date TEXT
            )
        """)
        await db.commit()
        logger.info("Database schema initialization completed")

# Управление ролями пользователей
async def get_user_role(user_id: int) -> str:
    """
    Получает роль пользователя по его ID. Если пользователь не существует, создаёт его с ролью 'user'.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            return row[0]
        await db.execute("INSERT INTO users (user_id, role) VALUES (?, ?)", (user_id, "user"))
        await db.commit()
        return "user"

async def set_user_role(user_id: int, role: str):
    """
    Устанавливает роль для пользователя.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        await db.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
        await db.commit()

async def remove_user_role(user_id: int, role: str) -> bool:
    """
    Удаляет указанную роль у пользователя, возвращая его к роли 'user'. Возвращает True, если роль была удалена.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row and row[0] == role:
            await db.execute("UPDATE users SET role = 'user' WHERE user_id = ?", (user_id,))
            await db.commit()
            return True
        return False

async def get_users_by_role(role: str) -> list:
    """
    Возвращает список ID пользователей с указанной ролью.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE role = ?", (role,))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

# Управление лимитами
async def check_limit(user_id: int, action_type: str) -> tuple[bool, int, int]:
    """
    Проверяет, не превышен ли лимит действия (view_news или create_news) для пользователя.
    Возвращает: (разрешено ли действие, текущий счётчик, общий лимит).
    """
    count_column = "view_count" if action_type == "view_news" else "create_count"
    limit_column = "view_limit" if action_type == "view_news" else "create_limit"
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            f"SELECT {count_column}, {limit_column} FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        if not row:
            await db.execute(
                "INSERT INTO users (user_id, role) VALUES (?, ?)",
                (user_id, "user")
            )
            await db.commit()
            return True, 0, 10 if action_type == "view_news" else 5
        current_count, total_limit = row
        return current_count < total_limit, current_count, total_limit

async def increment_limit(user_id: int, action_type: str):
    """
    Увеличивает счётчик использованных действий (view_news или create_news) для пользователя.
    """
    count_column = "view_count" if action_type == "view_news" else "create_count"
    async with aiosqlite.connect("news_bot.db") as db:
        await db.execute(
            f"UPDATE users SET {count_column} = {count_column} + 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()

async def add_limit(user_id: int, action_type: str, quantity: int):
    """
    Добавляет дополнительные лимиты для указанного действия (view_news или create_news).
    """
    limit_column = "view_limit" if action_type == "view_news" else "create_limit"
    async with aiosqlite.connect("news_bot.db") as db:
        await db.execute(
            f"UPDATE users SET {limit_column} = {limit_column} + ? WHERE user_id = ?",
            (quantity, user_id)
        )
        await db.commit()

# Управление покупками
async def add_purchase(user_id: int, action_type: str, amount: int, cost: int):
    """
    Сохраняет информацию о покупке лимитов пользователем.
    """
    purchase_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect("news_bot.db") as db:
        await db.execute(
            "INSERT INTO purchases (user_id, action_type, amount, cost, purchase_date) VALUES (?, ?, ?, ?, ?)",
            (user_id, action_type, amount, cost, purchase_date)
        )
        await db.commit()

# Статистика пользователя
async def get_user_stats(user_id: int) -> dict:
    """
    Получает статистику пользователя: роль, лимиты, лайки, дизлайки, покупки, новости (для писателей).
    """
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT role, view_count, view_limit, create_count, create_limit FROM users WHERE user_id = ?",
            (user_id,)
        )
        user_data = await cursor.fetchone()
        if not user_data:
            await db.execute(
                "INSERT INTO users (user_id, role) VALUES (?, ?)",
                (user_id, "user")
            )
            await db.commit()
            user_data = ("user", 0, 10, 0, 5)

        cursor = await db.execute(
            "SELECT COUNT(*) FROM ratings WHERE user_id = ? AND rating = 1",
            (user_id,)
        )
        likes = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM ratings WHERE user_id = ? AND rating = -1",
            (user_id,)
        )
        dislikes = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT action_type, amount, cost, purchase_date FROM purchases WHERE user_id = ? ORDER BY purchase_date DESC LIMIT 5",
            (user_id,)
        )
        purchases = [
            {"action_type": row[0], "amount": row[1], "cost": row[2], "purchase_date": row[3]}
            for row in await cursor.fetchall()
        ]

        published_news = 0
        pending_news = 0
        average_rating = 0.0
        if user_data[0] == "writer":
            cursor = await db.execute(
                "SELECT COUNT(*) FROM news WHERE writer_id = ?",
                (user_id,)
            )
            published_news = (await cursor.fetchone())[0]

            cursor = await db.execute(
                "SELECT COUNT(*) FROM pending_news WHERE writer_id = ?",
                (user_id,)
            )
            pending_news = (await cursor.fetchone())[0]

            cursor = await db.execute(
                "SELECT AVG(rating) FROM ratings WHERE news_id IN (SELECT news_id FROM news WHERE writer_id = ?)",
                (user_id,)
            )
            avg_rating = await cursor.fetchone()
            average_rating = avg_rating[0] if avg_rating[0] is not None else 0.0

        return {
            "role": user_data[0],
            "view_count": user_data[1],
            "view_limit": user_data[2],
            "create_count": user_data[3],
            "create_limit": user_data[4],
            "likes": likes,
            "dislikes": dislikes,
            "purchases": purchases,
            "published_news": published_news,
            "pending_news": pending_news,
            "average_rating": average_rating,
        }

# Управление новостями
async def get_news(category: str = None, limit: int = 10) -> list:
    """
    Получает список опубликованных новостей, отфильтрованных по категории (если указана).
    """
    async with aiosqlite.connect("news_bot.db") as db:
        query = "SELECT * FROM news"
        params = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        query += " LIMIT ?"
        params.append(limit)

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [
            {
                "news_id": row[0],
                "category": row[1],
                "title": row[2],
                "description": row[3],
                "image_url": row[4],
                "source": row[5],
                "published_at": row[6],
                "writer_id": row[7] if len(row) > 7 else None,
            }
            for row in rows
        ]

async def get_news_by_id(news_id: int) -> dict:
    """
    Получает информацию о конкретной новости по её ID.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute("SELECT * FROM news WHERE news_id = ?", (news_id,))
        row = await cursor.fetchone()
        if row:
            return {
                "news_id": row[0],
                "category": row[1],
                "title": row[2],
                "description": row[3],
                "image_url": row[4],
                "source": row[5],
                "published_at": row[6],
                "writer_id": row[7] if len(row) > 7 else None,
            }
        return None

async def insert_pending_news(writer_id: int, title: str, description: str, image_url: str, category: str) -> int:
    """
    Добавляет новость в очередь на проверку. Возвращает ID добавленной записи.
    """
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "INSERT INTO pending_news (writer_id, title, description, image_url, category, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (writer_id, title, description, image_url, category, created_at)
        )
        await db.commit()
        return cursor.lastrowid

async def update_pending_news(news_id: int, title: str, description: str, image_url: str, category: str, is_published: bool = False):
    """
    Обновляет данные новости (опубликованной или на проверке).
    """
    async with aiosqlite.connect("news_bot.db") as db:
        if is_published:
            await db.execute(
                "UPDATE news SET title = ?, description = ?, image_url = ?, category = ? WHERE news_id = ?",
                (title, description, image_url, category, news_id)
            )
        else:
            await db.execute(
                "UPDATE pending_news SET title = ?, description = ?, image_url = ?, category = ? WHERE pending_id = ?",
                (title, description, image_url, category, news_id)
            )
        await db.commit()

async def delete_pending_news(news_id: int, is_published: bool = False):
    """
    Удаляет новость (опубликованную или на проверке).
    """
    async with aiosqlite.connect("news_bot.db") as db:
        if is_published:
            await db.execute("DELETE FROM news WHERE news_id = ?", (news_id,))
        else:
            await db.execute("DELETE FROM pending_news WHERE pending_id = ?", (news_id,))
        await db.commit()

async def get_pending_news() -> list:
    """
    Получает список новостей, ожидающих проверки.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT pending_id, writer_id, title, description, image_url, category, created_at FROM pending_news"
        )
        rows = await cursor.fetchall()
        return [
            {
                "pending_id": row[0],
                "writer_id": row[1],
                "title": row[2],
                "description": row[3],
                "image_url": row[4],
                "category": row[5],
                "created_at": row[6],
            }
            for row in rows
        ]

async def approve_news(pending_id: int) -> int:
    """
    Одобряет новость, перемещая её из pending_news в news. Возвращает ID опубликованной новости.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT writer_id, title, description, image_url, category, created_at FROM pending_news WHERE pending_id = ?",
            (pending_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        writer_id, title, description, image_url, category, created_at = row
        published_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = await db.execute(
            "INSERT INTO news (category, title, description, image_url, source, published_at, writer_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (category, title, description, image_url, "Writer", published_at, writer_id)
        )
        news_id = cursor.lastrowid
        await db.execute("DELETE FROM pending_news WHERE pending_id = ?", (pending_id,))
        await db.commit()
        return news_id

async def reject_news(pending_id: int):
    """
    Отклоняет новость, удаляя её из pending_news.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        await db.execute("DELETE FROM pending_news WHERE pending_id = ?", (pending_id,))
        await db.commit()

# Управление рейтингами
async def set_news_rating(user_id: int, news_id: int, rating: int):
    """
    Устанавливает рейтинг (лайк или дизлайк) для новости от пользователя.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO ratings (user_id, news_id, rating) VALUES (?, ?, ?)",
            (user_id, news_id, rating)
        )
        await db.commit()

async def get_news_rating(news_id: int) -> tuple[int, int]:
    """
    Получает количество лайков и дизлайков для новости.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM ratings WHERE news_id = ? AND rating = 1",
            (news_id,)
        )
        likes = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM ratings WHERE news_id = ? AND rating = -1",
            (news_id,)
        )
        dislikes = (await cursor.fetchone())[0]

        return likes, dislikes

async def get_user_rating(user_id: int, news_id: int) -> int:
    """
    Получает рейтинг, установленный пользователем для конкретной новости.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT rating FROM ratings WHERE user_id = ? AND news_id = ?",
            (user_id, news_id)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

# Управление источниками
async def get_sources(category: str = None) -> list:
    """
    Получает список источников RSS, отфильтрованных по категории (если указана).
    """
    async with aiosqlite.connect("news_bot.db") as db:
        query = "SELECT * FROM sources"
        params = []
        if category:
            query += " WHERE category = ?"
            params.append(category)

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [
            {
                "source_id": row[0],
                "category": row[1],
                "url": row[2],
                "is_active": row[3],
            }
            for row in rows
        ]

# Управление подписками
async def get_user_subscriptions(user_id: int) -> list:
    """
    Получает список категорий, на которые подписан пользователь.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT category FROM subscriptions WHERE user_id = ?",
            (user_id,)
        )
        return [row[0] for row in await cursor.fetchall()]

async def subscribe_to_category(user_id: int, category: str) -> bool:
    """
    Подписывает пользователя на категорию. Возвращает False, если подписка уже существует.
    """
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
    """
    Отписывает пользователя от категории.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        await db.execute(
            "DELETE FROM subscriptions WHERE user_id = ? AND category = ?",
            (user_id, category)
        )
        await db.commit()
        return True

async def get_subscribers(category: str) -> list:
    """
    Получает список ID пользователей, подписанных на указанную категорию.
    """
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute(
            "SELECT user_id FROM subscriptions WHERE category = ?",
            (category,)
        )
        return [row[0] for row in await cursor.fetchall()]

# Управление новостями писателя
async def get_writer_news(writer_id: int) -> tuple[list, list]:
    """
    Получает списки опубликованных и ожидающих проверки новостей для писателя.
    """
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

        return published, pending