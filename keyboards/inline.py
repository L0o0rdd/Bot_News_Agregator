from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu(role: str) -> InlineKeyboardMarkup:
    kb = []
    if role == "admin":
        kb.append([InlineKeyboardButton(text="🛠 Админ-панель", callback_data="admin_panel")])
        kb.append([InlineKeyboardButton(text="📰 Посмотреть новости", callback_data="view_news")])
    elif role == "manager":
        kb.append([InlineKeyboardButton(text="📢 Панель менеджера", callback_data="manager_panel")])
        kb.append([InlineKeyboardButton(text="📰 Посмотреть новости", callback_data="view_news")])
    else:
        kb.append([InlineKeyboardButton(text="📰 Посмотреть новости", callback_data="view_news")])

    kb.append([InlineKeyboardButton(text="🚧 В разработке", callback_data="under_development")])

    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_admin_panel() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="👤 Назначить менеджера", callback_data="assign_manager")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_news_categories(refresh: bool = False, category: str = None) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🌍 Общие", callback_data="news_general")],
        [InlineKeyboardButton(text="💼 Бизнес", callback_data="news_business")],
        [InlineKeyboardButton(text="🧑‍💻 Технологии", callback_data="news_technology")],
        [InlineKeyboardButton(text="🎮 Развлечения", callback_data="news_entertainment")],
        [InlineKeyboardButton(text="⚽ Спорт", callback_data="news_sports")],
    ]
    if refresh and category:
        kb.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"news_{category}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)