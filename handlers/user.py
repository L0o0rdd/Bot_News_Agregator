import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from keyboards.inline import get_menu_keyboard, get_categories_keyboard, get_news_navigation, get_sources_keyboard, \
    get_subscription_keyboard, get_purchase_keyboard, get_quantity_keyboard, get_profile_keyboard
from utils.database import get_user_role, get_news, get_news_by_id, set_news_rating, get_news_rating, \
    get_user_rating, get_user_stats, check_limit, increment_limit, add_limit, add_purchase, get_user_subscriptions, \
    unsubscribe_from_category, subscribe_to_category, get_sources
from utils.payment import create_payment, check_payment
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
    user_id = callback.from_user.id
    allowed, current_count, total_limit = await check_limit(user_id, "view_news")
    if not allowed:
        await callback.message.edit_text(
            f"⚠️ У вас закончились лимиты на просмотр новостей ({current_count}/{total_limit})!\n"
            "Хотите купить дополнительные просмотры? 💎",
            reply_markup=get_purchase_keyboard("view_news")
        )
        await callback.answer()
        logger.info(f"User {user_id} reached view limit: {current_count}/{total_limit}")
        return

    await callback.message.edit_text(
        "📋 Выбери категорию новостей:",
        reply_markup=get_categories_keyboard()
    )
    await state.set_state(NewsViewing.viewing)
    await callback.answer()
    logger.info(f"User {callback.from_user.id} started viewing news.")

@router.callback_query(lambda c: c.data.startswith("category_"), NewsViewing.viewing)
async def select_category(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    allowed, current_count, total_limit = await check_limit(user_id, "view_news")
    if not allowed:
        await callback.message.edit_text(
            f"⚠️ У вас закончились лимиты на просмотр новостей ({current_count}/{total_limit})!\n"
            "Хотите купить дополнительные просмотры? 💎",
            reply_markup=get_purchase_keyboard("view_news")
        )
        await callback.answer()
        logger.info(f"User {user_id} reached view limit: {current_count}/{total_limit}")
        return

    await increment_limit(user_id, "view_news")
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
    user_id = callback.from_user.id
    allowed, current_count, total_limit = await check_limit(user_id, "view_news")
    if not allowed:
        await callback.message.edit_text(
            f"⚠️ У вас закончились лимиты на просмотр новостей ({current_count}/{total_limit})!\n"
            "Хотите купить дополнительные просмотры? 💎",
            reply_markup=get_purchase_keyboard("view_news")
        )
        await callback.answer()
        logger.info(f"User {user_id} reached view limit: {current_count}/{total_limit}")
        return

    await increment_limit(user_id, "view_news")
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
    response += f"📖 Лимит просмотров: {stats['view_count']}/{stats['view_limit']}\n"
    response += f"👍 Поставлено лайков: {stats['likes']}\n"
    response += f"👎 Поставлено дизлайков: {stats['dislikes']}\n"

    if stats["role"] == "writer":
        response += f"📝 Лимит постов: {stats['create_count']}/{stats['create_limit']}\n"
        response += f"\n✍️ Ваши новости:\n"
        response += f"- Опубликованные: {stats['published_news']}\n"
        response += f"- На проверке: {stats['pending_news']}\n"
        response += f"- Средний рейтинг: {stats['average_rating']:.2f}\n"

    response += "\n🛒 История покупок (последние 5):\n"
    if stats["purchases"]:
        for purchase in stats["purchases"]:
            action = "просмотров" if purchase["action_type"] == "view_news" else "постов"
            response += f"- {purchase['amount']} {action} за {purchase['cost']}₽ ({purchase['purchase_date']})\n"
    else:
        response += "Покупок пока нет.\n"

    await callback.message.edit_text(
        response,
        reply_markup=get_profile_keyboard(stats["role"])
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

@router.callback_query(lambda c: c.data.startswith("buy_limits_"))
async def buy_limits(callback: CallbackQuery):
    action_type = callback.data.split("_")[2]
    action_text = "просмотров" if action_type == "view_news" else "постов"
    await callback.message.edit_text(
        f"💎 Покупка дополнительных {action_text}\nВыберите количество:",
        reply_markup=get_quantity_keyboard(action_type)
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} started buying limits for {action_type}.")

@router.callback_query(lambda c: c.data.startswith("purchase_"))
async def process_purchase(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = callback.data.split("_")
    action_type = data[1]
    quantity = int(data[2])
    cost = int(data[3])
    action_text = "просмотров" if action_type == "view_news" else "постов"

    # Создаём платеж через ЮKassa
    description = f"Покупка {quantity} {action_text} в боте"
    payment = await create_payment(user_id, cost, description, action_type, quantity)
    if not payment:
        await callback.message.edit_text(
            "❌ Ошибка при создании платежа. Попробуйте позже.",
            reply_markup=get_menu_keyboard(await get_user_role(user_id))
        )
        await callback.answer()
        logger.error(f"Failed to create payment for user {user_id}")
        return

    payment_id = payment["id"]
    confirmation_url = payment["confirmation"]["confirmation_url"]

    # Сохраняем данные о платеже в состоянии
    await state.update_data(payment_id=payment_id, action_type=action_type, quantity=quantity, cost=cost)

    await callback.message.edit_text(
        f"💳 Для оплаты {quantity} {action_text} на сумму {cost}₽ перейдите по ссылке:\n{confirmation_url}\n\n"
        "После оплаты нажмите 'Проверить оплату' 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_payment_{payment_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
    )
    await callback.answer()
    logger.info(f"User {user_id} created payment {payment_id} for {quantity} {action_type}.")

@router.callback_query(lambda c: c.data.startswith("check_payment_"))
async def check_payment_status(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    payment_id = callback.data.split("_")[2]
    data = await state.get_data()
    if data.get("payment_id") != payment_id:
        await callback.message.edit_text(
            "❌ Неверный ID платежа.",
            reply_markup=get_menu_keyboard(await get_user_role(user_id))
        )
        await callback.answer()
        return

    payment = await check_payment(payment_id)
    if not payment:
        await callback.message.edit_text(
            "❌ Ошибка при проверке платежа. Попробуйте позже.",
            reply_markup=get_menu_keyboard(await get_user_role(user_id))
        )
        await callback.answer()
        return

    if payment["status"] == "succeeded":
        action_type = data["action_type"]
        quantity = data["quantity"]
        cost = data["cost"]
        action_text = "просмотров" if action_type == "view_news" else "постов"

        # Добавляем лимиты и запись о покупке
        await add_limit(user_id, action_type, quantity)
        await add_purchase(user_id, action_type, quantity, cost)

        await callback.message.edit_text(
            f"🎉 Оплата прошла успешно!\n"
            f"Вы приобрели {quantity} {action_text} за {cost}₽.\n"
            "Теперь вы можете продолжить! 👇",
            reply_markup=get_menu_keyboard(await get_user_role(user_id))
        )
        await state.clear()
        await callback.answer()
        logger.info(f"User {user_id} successfully purchased {quantity} {action_type} for {cost}₽.")
    else:
        await callback.message.edit_text(
            f"⏳ Платёж ещё не завершён (статус: {payment['status']}).\n"
            "Проверьте снова через несколько секунд.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_payment_{payment_id}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ])
        )
        await callback.answer()
        logger.info(f"User {user_id} checked payment {payment_id}, status: {payment['status']}.")