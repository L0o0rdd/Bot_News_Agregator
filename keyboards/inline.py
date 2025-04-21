from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu(role: str) -> InlineKeyboardMarkup:
    kb = []
    if role == "admin":
        kb.append([InlineKeyboardButton(text="🛠 Админ-панель", callback_data="admin_panel")])
        kb.append([InlineKeyboardButton(text="📰 Посмотреть новости", callback_data="view_news")])
    elif role == "manager":
        kb.append([InlineKeyboardButton(text="📢 Панель менеджера", callback_data="manager_panel")])
        kb.append([InlineKeyboardButton(text="📰 Посмотреть новости", callback_data="view_news")])
    elif role == "writer":
        kb.append([InlineKeyboardButton(text="✍️ Панель писателя", callback_data="writer_panel")])
        kb.append([InlineKeyboardButton(text="📰 Посмотреть новости", callback_data="view_news")])
    else:
        kb.append([InlineKeyboardButton(text="📰 Посмотреть новости", callback_data="view_news")])

    kb.append([InlineKeyboardButton(text="🚧 В разработке", callback_data="under_development")])

    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_admin_panel() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="👤 Назначить менеджера", callback_data="assign_manager")],
        [InlineKeyboardButton(text="✍️ Назначить писателя", callback_data="assign_writer")],
        [InlineKeyboardButton(text="📰 Проверить новости", callback_data="review_news")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_manager_panel() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="✍️ Назначить писателя", callback_data="assign_writer")],
        [InlineKeyboardButton(text="📰 Проверить новости", callback_data="review_news")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_writer_panel() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="📰 Создать новость", callback_data="create_news")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_news_categories(refresh: bool = False, category: str = None, page: int = 0, total_pages: int = 1,
                        active: bool = True, archive: bool = False) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🌍 Общие", callback_data=f"news_general")],
        [InlineKeyboardButton(text="💼 Бизнес", callback_data=f"news_business")],
        [InlineKeyboardButton(text="🧑‍💻 Технологии", callback_data=f"news_technology")],
        [InlineKeyboardButton(text="🎮 Развлечения", callback_data=f"news_entertainment")],
        [InlineKeyboardButton(text="⚽ Спорт", callback_data=f"news_sports")],
    ]
    if refresh and category:
        kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"news_{category}")])
        if total_pages > 1:
            nav = []
            if page > 0:
                nav.append(InlineKeyboardButton(text="⬅️ Назад",
                                                callback_data=f"news_page_{category}_{page - 1}_{'active' if active else 'archive'}"))
            if page < total_pages - 1:
                nav.append(InlineKeyboardButton(text="Вперёд ➡️",
                                                callback_data=f"news_page_{category}_{page + 1}_{'active' if active else 'archive'}"))
            if nav:
                kb.append(nav)
    if not archive:
        kb.append([InlineKeyboardButton(text="🗄 Показать архив", callback_data="show_archive")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_category_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🌍 Общие", callback_data="category_general")],
        [InlineKeyboardButton(text="💼 Бизнес", callback_data="category_business")],
        [InlineKeyboardButton(text="🧑‍💻 Технологии", callback_data="category_technology")],
        [InlineKeyboardButton(text="🎮 Развлечения", callback_data="category_entertainment")],
        [InlineKeyboardButton(text="⚽ Спорт", callback_data="category_sports")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_confirmation_keyboard(confirm_data: str, cancel_data: str) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_data)],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=cancel_data)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)