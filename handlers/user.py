from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from keyboards.inline import get_news_categories, get_source_selection_keyboard
from utils.news import get_news as get_rss_news
from utils.database import get_news, get_news_count
from config.config import RSS_FEEDS

router = Router()


@router.callback_query(lambda c: c.data == "view_news")
async def view_news(callback: CallbackQuery):
    await callback.message.edit_text(
        "📰 Выберите категорию новостей:",
        reply_markup=get_news_categories()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("news_"))
async def show_news(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    category = parts[1]
    page = 0
    active = True
    source = None

    if callback.data.startswith("news_page_"):
        category = parts[2]
        page = int(parts[3])
        active = parts[4] == "active"
        source = parts[5] if len(parts) > 5 and parts[5] != "all" else None
    elif callback.data.startswith("news_source_"):
        category = parts[2]
        source = parts[3]

    # Получаем пользовательские новости
    user_news = await get_news(category, active=active, limit=3, offset=page * 3)
    total_user_news = await get_news_count(category, active=active)

    # Получаем RSS-новости
    rss_news = get_rss_news(category, source=source, max_results=2)

    response = f"📰 Новости ({category.capitalize()}):\n\n"

    # Пользовательские новости
    if user_news:
        response += "📝 Пользовательские новости:\n"
        for i, article in enumerate(user_news, 1):
            response += f"{i}. *{article['title']}*\n{article['description']}\n"
            if article['image_url']:
                response += f"🖼 [Картинка]({article['image_url']})\n"
            response += f"👤 Автор ID: {article['author_id']}\n\n"

    # RSS-новости
    if rss_news:
        response += "🗞 RSS-новости:\n"
        for i, article in enumerate(rss_news, 1):
            response += f"{i}. *{article['title']}* ({article['source']})\n{article['description']}\n🔗 [Читать далее]({article['url']})\n\n"

    if not user_news and not rss_news:
        response += "😔 Нет новостей в этой категории.\n"

    try:
        await callback.message.edit_text(
            response,
            parse_mode="Markdown",
            reply_markup=get_news_categories(
                refresh=True,
                category=category,
                page=page,
                total_pages=(total_user_news + 2) // 3,
                active=active,
                source=source
            )
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("📰 Новости уже актуальны!", show_alert=True)
        else:
            raise
    await callback.answer()


@router.callback_query(lambda c: c.data == "show_archive")
async def show_archive(callback: CallbackQuery):
    await callback.message.edit_text(
        "🗄 Выберите категорию для архива:",
        reply_markup=get_news_categories(archive=True)
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("select_source_"))
async def select_source(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    category = parts[2]
    feeds = RSS_FEEDS.get(category, [])
    if not feeds:
        await callback.message.edit_text(
            "😔 Нет источников для этой категории.",
            reply_markup=get_news_categories()
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        f"🗞 Выберите источник для категории {category.capitalize()}:",
        reply_markup=get_source_selection_keyboard(feeds, category)
    )
    await callback.answer()