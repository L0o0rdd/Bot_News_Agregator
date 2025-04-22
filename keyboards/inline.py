from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config.config import RSS_FEEDS


def get_menu_keyboard(role: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📖 Посмотреть новости", callback_data="view_news")],
        [InlineKeyboardButton(text="🔔 Управление подписками", callback_data="manage_subscriptions")],
        [InlineKeyboardButton(text="📡 Фильтровать источники", callback_data="filter_sources")],
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")],
    ]
    if role == "writer":
        buttons.append([InlineKeyboardButton(text="✍️ Панель писателя", callback_data="writer_panel")])
    if role in ["admin", "manager"]:
        buttons.append([InlineKeyboardButton(text="🛠 Панель управления", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_categories_keyboard() -> InlineKeyboardMarkup:
    categories = list(RSS_FEEDS.keys())
    buttons = [
        [InlineKeyboardButton(text=category.capitalize(), callback_data=f"category_{category}")]
        for category in categories
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_subscription_keyboard(subscribed_categories: list) -> InlineKeyboardMarkup:
    categories = list(RSS_FEEDS.keys())
    buttons = []
    for category in categories:
        if category in subscribed_categories:
            buttons.append(
                [InlineKeyboardButton(text=f"✅ {category.capitalize()}", callback_data=f"unsubscribe_{category}")]
            )
        else:
            buttons.append(
                [InlineKeyboardButton(text=f"⬜ {category.capitalize()}", callback_data=f"subscribe_{category}")]
            )
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_news_navigation(news: list, current_index: int, category: str) -> InlineKeyboardMarkup:
    buttons = []
    if current_index > 0:
        buttons.append(InlineKeyboardButton(text="⬅️ Пред", callback_data=f"prev_news_{current_index}"))
    if current_index < len(news) - 1:
        buttons.append(InlineKeyboardButton(text="След ➡️", callback_data=f"next_news_{current_index}"))
    row = []
    if buttons:
        row.extend(buttons)
    row.append(InlineKeyboardButton(text="👍 Лайк", callback_data=f"like_news_{news[current_index]['news_id']}"))
    row.append(InlineKeyboardButton(text="👎 Дизлайк", callback_data=f"dislike_news_{news[current_index]['news_id']}"))
    buttons_row = [row]
    buttons_row.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"category_{category}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons_row)


def get_writer_news_keyboard(published: list, pending: list) -> InlineKeyboardMarkup:
    buttons = []

    # Добавляем кнопку "Создать новость" всегда
    buttons.append([InlineKeyboardButton(text="🖌 Создать новость", callback_data="create_news")])

    # Отображаем опубликованные новости
    if published:
        buttons.append([InlineKeyboardButton(text="📢 Опубликованные новости", callback_data="view_published")])
        for news in published:
            buttons.append([
                InlineKeyboardButton(
                    text=f"📰 {news['title'][:20]}...",
                    callback_data=f"view_published_{news['news_id']}"
                ),
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data=f"edit_published_{news['news_id']}"
                ),
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"delete_published_{news['news_id']}"
                ),
            ])

    # Отображаем новости на проверке
    if pending:
        buttons.append([InlineKeyboardButton(text="⏳ Новости на проверке", callback_data="view_pending")])
        for news in pending:
            buttons.append([
                InlineKeyboardButton(
                    text=f"📰 {news['title'][:20]}...",
                    callback_data=f"view_pending_{news['pending_id']}"
                ),
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data=f"edit_pending_{news['pending_id']}"
                ),
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"delete_pending_{news['pending_id']}"
                ),
            ])

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_sources_keyboard(sources: list, category: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"🌐 {source['url'][:20]}...",
                              callback_data=f"source_{source['source_id']}_{category}")]
        for source in sources
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="filter_sources")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_purchase_keyboard(action: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="💎 Купить дополнительные лимиты", callback_data=f"buy_limits_{action}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quantity_keyboard(action: str) -> InlineKeyboardMarkup:
    if action == "view_news":
        buttons = [
            [InlineKeyboardButton(text="5 просмотров за 10P", callback_data="buy_views_5_10")],
            [InlineKeyboardButton(text="10 просмотров за 15P", callback_data="buy_views_10_15")],
            [InlineKeyboardButton(text="20 просмотров за 25P", callback_data="buy_views_20_25")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton(text="5 постов за 10P", callback_data="buy_posts_5_10")],
            [InlineKeyboardButton(text="10 постов за 15P", callback_data="buy_posts_10_15")],
            [InlineKeyboardButton(text="20 постов за 25P", callback_data="buy_posts_20_25")],
        ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="profile")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_profile_keyboard(role: str) -> InlineKeyboardMarkup:
    buttons = []
    if role != "admin":
        buttons.append([InlineKeyboardButton(text="💎 Купить дополнительные лимиты", callback_data="buy_limits_view")])
    if role == "writer":
        buttons.append([InlineKeyboardButton(text="✍️ Панель писателя", callback_data="writer_panel")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📋 Проверить новости", callback_data="review_news")],
        [InlineKeyboardButton(text="👥 Управление ролями", callback_data="manage_roles")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_manager_panel() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📋 Проверить новости", callback_data="review_news")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_role_management_keyboard(users: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"👤 User {user['user_id']}", callback_data=f"set_role_{user['user_id']}")]
        for user in users
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_role_selection_keyboard(user_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="👤 Пользователь", callback_data=f"role_user_{user_id}")],
        [InlineKeyboardButton(text="✍️ Писатель", callback_data=f"role_writer_{user_id}")],
        [InlineKeyboardButton(text="🛠 Менеджер", callback_data=f"role_manager_{user_id}")],
        [InlineKeyboardButton(text="👑 Админ", callback_data=f"role_admin_{user_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="manage_roles")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pending_news_keyboard(news: list) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text=f"📰 {n['title'][:20]}...", callback_data=f"view_pending_{n['pending_id']}"),
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{n['pending_id']}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{n['pending_id']}")
        ]
        for n in news
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)