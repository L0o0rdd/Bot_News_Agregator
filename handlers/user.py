import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from keyboards.inline import get_menu_keyboard, get_categories_keyboard, get_news_navigation, get_sources_keyboard, \
    get_subscription_keyboard
from utils.database import get_user_role, get_news, get_news_by_id, get_sources, set_news_rating, get_news_rating, \
    get_user_rating, get_user_stats, get_user_subscriptions, subscribe_to_category, unsubscribe_from_category
from utils.logger import logger

router = Router()


class NewsViewing(StatesGroup):
    viewing = State()


class SourceFiltering(StatesGroup):
    filtering = State()


@router.message(Command("start"))
async def start(message: Message):
    role = await get_user_role(message.from_user.id)
    if role == "admin":
        greeting = "👋 Привет, администратор! Ты можешь управлять ботом и проверять новости."
    elif role == "manager":
        greeting = "👋 Привет, менеджер! Ты можешь проверять новости и назначать писателей."
    elif role == "writer":
        greeting = "👋 Привет, писатель! Ты можешь создавать и редактировать новости."
    else:
        greeting = "👋 Привет! Я бот для просмотра и управления новостями. Выбери действие ниже 👇"

    await message.answer(
        greeting,
        reply_markup=get_menu_keyboard(role)
    )
    logger.info(f"User {message.from_user.id} started bot. Role: {role}")


@router.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    role = await get_user_role(callback.from_user.id)
    await callback.message.edit_text(
        "👋 Главное меню\nВыбери действие ниже 👇",
        reply_markup=get_menu_keyboard(role)
    )
    await state.clear()
    await callback.answer()
    logger.info(f"User {callback.from_user.id} returned to main menu.")


@router.callback_query(lambda c: c.data == "view_news")
async def view_news(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📋 Выбери категорию новостей:",
        reply_markup=get_categories_keyboard()
    )
    await state.set_state(NewsViewing.viewing)
    await callback.answer()
    logger.info(f"User {callback.from_user.id} started viewing news.")


@router.callback_query(lambda c: c.data.startswith("category_"), NewsViewing.viewing)
async def select_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("_")[1]
    news = await get_news(category=category, limit=10)
    if not news:
        await callback.message.edit_text(
            f"📭 Новостей в категории {category.capitalize()} пока нет.",
            reply_markup=get_categories_keyboard()
        )
        await callback.answer()
        logger.info(f"User {callback.from_user.id} found no news in category {category}.")
        return

    await state.update_data(news=news, current_index=0, category=category)
    news_item = news[0]
    likes, dislikes = await get_news_rating(news_item["news_id"])
    user_rating = await get_user_rating(callback.from_user.id, news_item["news_id"])
    rating_text = f"👍 {likes} | 👎 {dislikes} | Ваш голос: {'👍' if user_rating == 1 else '👎' if user_rating == -1 else 'не оценено'}"

    response = (
        f"📰 Новость (ID: {news_item['news_id']})\n"
        f"Категория: {news_item['category'].capitalize()}\n"
        f"Заголовок: {news_item['title']}\n"
        f"Описание: {news_item['description']}\n"
    )
    if news_item['image_url']:
        response += f"🖼 Картинка: {news_item['image_url']}\n"
    response += f"Источник: {news_item['source']}\n"
    response += f"Опубликовано: {news_item['published_at']}\n"
    response += f"Рейтинг: {rating_text}"

    await callback.message.edit_text(
        response,
        reply_markup=get_news_navigation(news, 0, category)
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} viewed news ID {news_item['news_id']} in category {category}.")


@router.callback_query(lambda c: c.data.startswith("prev_news_") or c.data.startswith("next_news_"),
                       NewsViewing.viewing)
async def navigate_news(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    news = data.get("news", [])
    current_index = data.get("current_index", 0)
    category = data.get("category")

    if callback.data.startswith("prev_news_"):
        current_index -= 1
    else:
        current_index += 1

    await state.update_data(current_index=current_index)
    news_item = news[current_index]
    likes, dislikes = await get_news_rating(news_item["news_id"])
    user_rating = await get_user_rating(callback.from_user.id, news_item["news_id"])
    rating_text = f"👍 {likes} | 👎 {dislikes} | Ваш голос: {'👍' if user_rating == 1 else '👎' if user_rating == -1 else 'не оценено'}"

    response = (
        f"📰 Новость (ID: {news_item['news_id']})\n"
        f"Категория: {news_item['category'].capitalize()}\n"
        f"Заголовок: {news_item['title']}\n"
        f"Описание: {news_item['description']}\n"
    )
    if news_item['image_url']:
        response += f"🖼 Картинка: {news_item['image_url']}\n"
    response += f"Источник: {news_item['source']}\n"
    response += f"Опубликовано: {news_item['published_at']}\n"
    response += f"Рейтинг: {rating_text}"

    await callback.message.edit_text(
        response,
        reply_markup=get_news_navigation(news, current_index, category)
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} navigated to news ID {news_item['news_id']} in category {category}.")


@router.callback_query(lambda c: c.data.startswith("like_news_"))
async def like_news(callback: CallbackQuery, state: FSMContext):
    news_id = int(callback.data.split("_")[2])
    await set_news_rating(callback.from_user.id, news_id, 1)
    data = await state.get_data()
    news = data.get("news", [])
    current_index = data.get("current_index", 0)
    category = data.get("category")
    news_item = await get_news_by_id(news_id)
    likes, dislikes = await get_news_rating(news_id)
    user_rating = await get_user_rating(callback.from_user.id, news_id)
    rating_text = f"👍 {likes} | 👎 {dislikes} | Ваш голос: {'👍' if user_rating == 1 else '👎' if user_rating == -1 else 'не оценено'}"

    response = (
        f"📰 Новость (ID: {news_item['news_id']})\n"
        f"Категория: {news_item['category'].capitalize()}\n"
        f"Заголовок: {news_item['title']}\n"
        f"Описание: {news_item['description']}\n"
    )
    if news_item['image_url']:
        response += f"🖼 Картинка: {news_item['image_url']}\n"
    response += f"Источник: {news_item['source']}\n"
    response += f"Опубликовано: {news_item['published_at']}\n"
    response += f"Рейтинг: {rating_text}"

    await callback.message.edit_text(
        response,
        reply_markup=get_news_navigation(news, current_index, category)
    )
    await callback.answer("👍 Вы поставили лайк!")
    logger.info(f"User {callback.from_user.id} liked news ID {news_id}.")


@router.callback_query(lambda c: c.data.startswith("dislike_news_"))
async def dislike_news(callback: CallbackQuery, state: FSMContext):
    news_id = int(callback.data.split("_")[2])
    await set_news_rating(callback.from_user.id, news_id, -1)
    data = await state.get_data()
    news = data.get("news", [])
    current_index = data.get("current_index", 0)
    category = data.get("category")
    news_item = await get_news_by_id(news_id)
    likes, dislikes = await get_news_rating(news_id)
    user_rating = await get_user_rating(callback.from_user.id, news_id)
    rating_text = f"👍 {likes} | 👎 {dislikes} | Ваш голос: {'👍' if user_rating == 1 else '👎' if user_rating == -1 else 'не оценено'}"

    response = (
        f"📰 Новость (ID: {news_item['news_id']})\n"
        f"Категория: {news_item['category'].capitalize()}\n"
        f"Заголовок: {news_item['title']}\n"
        f"Описание: {news_item['description']}\n"
    )
    if news_item['image_url']:
        response += f"🖼 Картинка: {news_item['image_url']}\n"
    response += f"Источник: {news_item['source']}\n"
    response += f"Опубликовано: {news_item['published_at']}\n"
    response += f"Рейтинг: {rating_text}"

    await callback.message.edit_text(
        response,
        reply_markup=get_news_navigation(news, current_index, category)
    )
    await callback.answer("👎 Вы поставили дизлайк!")
    logger.info(f"User {callback.from_user.id} disliked news ID {news_id}.")


@router.callback_query(lambda c: c.data == "filter_sources")
async def filter_sources(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📋 Выбери категорию источников:",
        reply_markup=get_categories_keyboard()
    )
    await state.set_state(SourceFiltering.filtering)
    await callback.answer()
    logger.info(f"User {callback.from_user.id} started filtering sources.")


@router.callback_query(lambda c: c.data.startswith("category_"), SourceFiltering.filtering)
async def select_source_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("_")[1]
    sources = await get_sources(category=category)
    if not sources:
        await callback.message.edit_text(
            f"📭 Источников в категории {category.capitalize()} пока нет.",
            reply_markup=get_categories_keyboard()
        )
        await callback.answer()
        logger.info(f"User {callback.from_user.id} found no sources in category {category}.")
        return

    await state.update_data(category=category)
    await callback.message.edit_text(
        f"📡 Источники в категории {category.capitalize()}:",
        reply_markup=get_sources_keyboard(sources, category)
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} viewed sources in category {category}.")


@router.callback_query(lambda c: c.data.startswith("source_"), SourceFiltering.filtering)
async def toggle_source(callback: CallbackQuery, state: FSMContext):
    data = callback.data.split("_")
    source_id = int(data[1])
    category = data[2]
    sources = await get_sources(category=category)
    for source in sources:
        if source["source_id"] == source_id:
            source["is_active"] = 1 if source["is_active"] == 0 else 0
            async with aiosqlite.connect("news_bot.db") as db:
                await db.execute(
                    "UPDATE sources SET is_active = ? WHERE source_id = ?",
                    (source["is_active"], source_id)
                )
                await db.commit()
            break

    await callback.message.edit_text(
        f"📡 Источники в категории {category.capitalize()}:",
        reply_markup=get_sources_keyboard(sources, category)
    )
    await callback.answer("✅ Статус источника изменён!")
    logger.info(f"User {callback.from_user.id} toggled source ID {source_id} in category {category}.")


@router.callback_query(lambda c: c.data == "profile")
async def show_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    stats = await get_user_stats(user_id)

    response = f"👤 Личный кабинет\n\n"
    response += f"🧑 Роль: {stats['role'].capitalize()}\n"
    response += f"👍 Поставлено лайков: {stats['likes']}\n"
    response += f"👎 Поставлено дизлайков: {stats['dislikes']}\n\n"
    response += "🏆 Топ-3 лайкнутых новостей:\n"
    if stats['liked_news']:
        for news in stats['liked_news']:
            response += f"- ID {news['news_id']}: {news['title']}\n"
    else:
        response += "Вы пока не лайкнули ни одну новость.\n"

    if stats["role"] == "writer":
        response += f"\n✍️ Ваши новости:\n"
        response += f"- Опубликованные: {stats['published_news']}\n"
        response += f"- На проверке: {stats['pending_news']}\n"
        response += f"- Средний рейтинг: {stats['average_rating']:.2f}\n"

    if stats["role"] == "manager":
        response += f"\n📢 Ваша активность:\n"
        response += f"- Одобрено новостей: {stats['approved_news']}\n"
        response += f"- Отклонено новостей: {stats['rejected_news']}\n"

    if stats["role"] == "admin":
        response += f"\n🛠 Админ-активность:\n"
        response += f"- Назначено ролей: {stats['roles_assigned']}\n"
        response += f"- Удалено ролей: {stats['roles_removed']}\n\n"
        response += "📊 Общая статистика:\n"
        response += f"- 👥 Всего пользователей: {stats['general_stats']['total_users']}\n"
        response += f"- 👤 Менеджеров: {stats['general_stats']['managers']}\n"
        response += f"- ✍️ Писателей: {stats['general_stats']['writers']}\n"
        response += "📰 Новости по категориям:\n"
        for category, count in stats['general_stats']['news_by_category'].items():
            response += f"  - {category.capitalize()}: {count}\n"

    await callback.message.edit_text(
        response,
        reply_markup=get_menu_keyboard(stats["role"])
    )
    await callback.answer()
    logger.info(f"User {user_id} viewed their profile.")


@router.callback_query(lambda c: c.data == "manage_subscriptions")
async def manage_subscriptions(callback: CallbackQuery):
    user_id = callback.from_user.id
    subscribed_categories = await get_user_subscriptions(user_id)

    await callback.message.edit_text(
        "🔔 Управление подписками\nНажмите на категорию, чтобы подписаться или отписаться:",
        reply_markup=get_subscription_keyboard(subscribed_categories)
    )
    await callback.answer()
    logger.info(f"User {user_id} opened subscription management.")


@router.callback_query(lambda c: c.data.startswith("subscribe_"))
async def subscribe_category(callback: CallbackQuery):
    user_id = callback.from_user.id
    category = callback.data.split("_")[1]
    if await subscribe_to_category(user_id, category):
        subscribed_categories = await get_user_subscriptions(user_id)
        await callback.message.edit_text(
            "🔔 Управление подписками\nНажмите на категорию, чтобы подписаться или отписаться:",
            reply_markup=get_subscription_keyboard(subscribed_categories)
        )
        await callback.answer(f"✅ Вы подписались на категорию {category.capitalize()}!")
        logger.info(f"User {user_id} subscribed to category {category}.")
    else:
        await callback.answer("❌ Ошибка при подписке. Попробуйте снова.", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("unsubscribe_"))
async def unsubscribe_category(callback: CallbackQuery):
    user_id = callback.from_user.id
    category = callback.data.split("_")[1]
    if await unsubscribe_from_category(user_id, category):
        subscribed_categories = await get_user_subscriptions(user_id)
        await callback.message.edit_text(
            "🔔 Управление подписками\nНажмите на категорию, чтобы подписаться или отписаться:",
            reply_markup=get_subscription_keyboard(subscribed_categories)
        )
        await callback.answer(f"❌ Вы отписались от категории {category.capitalize()}!")
        logger.info(f"User {user_id} unsubscribed from category {category}.")
    else:
        await callback.answer("❌ Ошибка при отписке. Попробуйте снова.", show_alert=True)