from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from keyboards.inline import get_news_categories
from utils.news import get_news as get_rss_news
from utils.database import get_news, get_news_count

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
    category = callback.data.split("_")[1]
    page = 0
    active = True

    if callback.data.startswith("news_page_"):
        parts = callback.data.split("_")
        category = parts[2]
        page = int(parts[3])
        active = parts[4] == "active"

    news = await get_news(category, active=active, limit=5, offset=page * 5)
    total_news = await get_news_count(category, active=active)

    if not news:
        # Если нет новостей в базе, пробуем RSS
        news = get_rss_news(category)
        response = f"📰 Новости ({category.capitalize()}) (RSS):\n\n"
        for i, article in enumerate(news, 1):
            response += f"{i}. *{article['title']}* ({article['source']})\n{article['description']}\n🔗 [Читать далее]({article['url']})\n\n"
    else:
        response = f"📰 Новости ({category.capitalize()}):\n\n"
        for i, article in enumerate(news, 1):
            response += f"{i}. *{article['title']}*\n{article['description']}\n"
            if article['image_url']:
                response += f"🖼 [Картинка]({article['image_url']})\n"
            response += f"👤 Автор ID: {article['author_id']}\n\n"

    try:
        await callback.message.edit_text(
            response,
            parse_mode="Markdown",
            reply_markup=get_news_categories(
                refresh=True,
                category=category,
                page=page,
                total_pages=(total_news + 4) // 5,
                active=active
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