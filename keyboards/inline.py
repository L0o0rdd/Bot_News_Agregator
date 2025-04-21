from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_menu_keyboard(role: str) -> InlineKeyboardMarkup:
    kb = []
    if role == "admin":
        kb.append([InlineKeyboardButton(text="🛠 Админ-панель", callback_data="admin_panel")])
    elif role == "manager":
        kb.append([InlineKeyboardButton(text="📢 Панель менеджера", callback_data="manager_panel")])
    elif role == "writer":
        kb.append([InlineKeyboardButton(text="✍️ Панель писателя", callback_data="writer_panel")])

    kb.extend([
        [InlineKeyboardButton(text="📰 Просмотреть новости", callback_data="view_news")],
        [InlineKeyboardButton(text="📋 Фильтровать источники", callback_data="filter_sources")],
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")],
        [InlineKeyboardButton(text="🔔 Управление подписками", callback_data="manage_subscriptions")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_admin_panel() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="👤 Назначить менеджера", callback_data="assign_manager")],
        [InlineKeyboardButton(text="✍️ Назначить писателя", callback_data="assign_writer")],
        [InlineKeyboardButton(text="🗑 Удалить менеджера", callback_data="remove_manager")],
        [InlineKeyboardButton(text="🗑 Удалить писателя", callback_data="remove_writer")],
        [InlineKeyboardButton(text="📰 Проверить новости", callback_data="review_news")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📡 Управление RSS", callback_data="manage_rss")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_manager_panel() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="✍️ Назначить писателя", callback_data="assign_writer")],
        [InlineKeyboardButton(text="🗑 Удалить писателя", callback_data="remove_writer")],
        [InlineKeyboardButton(text="📰 Проверить новости", callback_data="review_news")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_writer_panel() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🖌 Создать новость", callback_data="create_news")],
        [InlineKeyboardButton(text="✍️ Редактировать новость", callback_data="edit_news")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_confirmation_keyboard(confirm_data: str, cancel_data: str) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_data)],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=cancel_data)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_user_selection_keyboard(users: list, action: str) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text=f"ID: {user_id}", callback_data=f"select_user_{action}_{user_id}")]
        for user_id in users
    ]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_categories_keyboard() -> InlineKeyboardMarkup:
    categories = ["general", "business", "technology", "entertainment", "sports"]
    kb = [
        [InlineKeyboardButton(text=category.capitalize(), callback_data=f"category_{category}")]
        for category in categories
    ]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_news_navigation(news: list, current_index: int, category: str = None) -> InlineKeyboardMarkup:
    kb = []
    news_id = news[current_index]["news_id"]
    kb.append([
        InlineKeyboardButton(text="👍", callback_data=f"like_news_{news_id}"),
        InlineKeyboardButton(text="👎", callback_data=f"dislike_news_{news_id}"),
    ])
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"prev_news_{category}_{current_index}"))
    if current_index < len(news) - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"next_news_{category}_{current_index}"))
    if nav_buttons:
        kb.append(nav_buttons)
    kb.append([InlineKeyboardButton(text="🔙 К категориям", callback_data="view_news")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_sources_keyboard(sources: list, category: str) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text=f"{source['category'].capitalize()}: {source['url']}",
                              callback_data=f"source_{source['source_id']}_{category}")]
        for source in sources
    ]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_rss_management_keyboard(sources: list) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(
            text=f"{source['category'].capitalize()}: {source['url']} {'✅' if source['is_active'] else '❌'}",
            callback_data=f"toggle_source_{source['source_id']}"
        )] for source in sources
    ]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_writer_news_keyboard(published: list, pending: list) -> InlineKeyboardMarkup:
    kb = []
    if published:
        kb.append([InlineKeyboardButton(text="📜 Опубликованные новости", callback_data="dummy")])
        for news in published:
            kb.append([
                InlineKeyboardButton(
                    text=f"ID {news['news_id']}: {news['title']}",
                    callback_data=f"edit_published_{news['news_id']}"
                )
            ])
    if pending:
        kb.append([InlineKeyboardButton(text="⏳ Новости на проверке", callback_data="dummy")])
        for news in pending:
            kb.append([
                InlineKeyboardButton(
                    text=f"ID {news['pending_id']}: {news['title']}",
                    callback_data=f"edit_pending_{news['pending_id']}"
                )
            ])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="writer_panel")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_subscription_keyboard(subscribed_categories: list) -> InlineKeyboardMarkup:
    categories = ["general", "business", "technology", "entertainment", "sports"]
    kb = []
    for category in categories:
        is_subscribed = category in subscribed_categories
        kb.append([
            InlineKeyboardButton(
                text=f"{category.capitalize()} {'✅' if is_subscribed else '❌'}",
                callback_data=f"{'unsubscribe' if is_subscribed else 'subscribe'}_{category}"
            )
        ])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_purchase_keyboard(action_type: str) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="💎 Купить дополнительные лимиты", callback_data=f"buy_limits_{action_type}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_quantity_keyboard(action_type: str) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="5 шт. (10₽)", callback_data=f"purchase_{action_type}_5_10")],
        [InlineKeyboardButton(text="10 шт. (15₽)", callback_data=f"purchase_{action_type}_10_15")],
        [InlineKeyboardButton(text="20 шт. (25₽)", callback_data=f"purchase_{action_type}_20_25")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_profile_keyboard(role: str) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="💎 Купить просмотры", callback_data="buy_limits_view_news")]
    ]
    if role == "writer":
        kb.append([InlineKeyboardButton(text="💎 Купить посты", callback_data="buy_limits_create_news")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)