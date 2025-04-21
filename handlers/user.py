from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from keyboards.inline import get_news_categories
from utils.news import get_news

router = Router()


@router.callback_query(lambda c: c.data == "view_news")
async def view_news(callback: CallbackQuery):
    await callback.message.edit_text(
        "📰 Выберите категорию новостей:",
        reply_markup=get_news_categories()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("news_"))
async def show_news(callback: CallbackQuery):
    category = callback.data.split("_")[1]
    news = get_news(category)

    if not news or "Ошибка" in news[0]["title"]:
        await callback.message.edit_text(
            "😔 Не удалось загрузить новости. Попробуйте позже.",
            reply_markup=get_news_categories()
        )
    else:
        response = f"📰 Новости ({category.capitalize()}):\n\n"
        for i, article in enumerate(news, 1):
            response += f"{i}. *{article['title']}* ({article['source']})\n{article['description']}\n🔗 [Читать далее]({article['url']})\n\n"

        try:
            await callback.message.edit_text(
                response,
                parse_mode="Markdown",
                reply_markup=get_news_categories(refresh=True, category=category)
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer("📰 Новости уже актуальны!", show_alert=True)
            else:
                raise
    await callback.answer()