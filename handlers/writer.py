from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.inline import get_writer_panel, get_categories_keyboard, get_confirmation_keyboard, \
    get_writer_news_keyboard, get_purchase_keyboard, get_quantity_keyboard, get_menu_keyboard
from utils.database import get_user_role, add_pending_news, get_writer_news, get_news_by_id, update_news, \
    update_pending_news, check_limit, increment_limit, add_limit, add_purchase, get_pending_news
from utils.payment import create_payment, check_payment
from utils.logger import logger

router = Router()


class NewsCreation(StatesGroup):
    category = State()
    title = State()
    description = State()
    image_url = State()
    confirmation = State()


class NewsEditing(StatesGroup):
    selecting = State()
    category = State()
    title = State()
    description = State()
    image_url = State()
    confirmation = State()


@router.callback_query(lambda c: c.data == "writer_panel")
async def writer_panel(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "writer":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    await callback.message.edit_text(
        "✍️ Панель писателя\nВыберите действие 👇",
        reply_markup=get_writer_panel()
    )
    await callback.answer()
    logger.info(f"Writer {callback.from_user.id} opened writer panel.")


@router.callback_query(lambda c: c.data == "create_news")
async def create_news(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if await get_user_role(user_id) != "writer":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return

    allowed, current_count, total_limit = await check_limit(user_id, "create_news")
    if not allowed:
        await callback.message.edit_text(
            f"⚠️ У вас закончились лимиты на создание новостей ({current_count}/{total_limit})!\n"
            "Хотите купить дополнительные лимиты? 💎",
            reply_markup=get_purchase_keyboard("create_news")
        )
        await callback.answer()
        logger.info(f"Writer {user_id} reached create limit: {current_count}/{total_limit}")
        return

    await callback.message.edit_text(
        "📋 Выберите категорию для новости:",
        reply_markup=get_categories_keyboard()
    )
    await state.set_state(NewsCreation.category)
    await callback.answer()
    logger.info(f"Writer {callback.from_user.id} started creating news.")


@router.callback_query(lambda c: c.data.startswith("category_"), NewsCreation.category)
async def process_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("_")[1]
    await state.update_data(category=category)
    await callback.message.edit_text(
        "📝 Введите заголовок новости:",
        reply_markup=None
    )
    await state.set_state(NewsCreation.title)
    await callback.answer()
    logger.info(f"Writer {callback.from_user.id} selected category {category} for news creation.")


@router.message(NewsCreation.title)
async def process_title(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "writer":
        await message.answer("🚫 Доступ запрещён!")
        return
    await state.update_data(title=message.text)
    await message.answer(
        "📜 Введите описание новости:"
    )
    await state.set_state(NewsCreation.description)
    logger.info(f"Writer {message.from_user.id} set news title: {message.text}")


@router.message(NewsCreation.description)
async def process_description(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "writer":
        await message.answer("🚫 Доступ запрещён!")
        return
    await state.update_data(description=message.text)
    await message.answer(
        "🖼 Введите URL картинки (или отправьте 'нет', чтобы пропустить):"
    )
    await state.set_state(NewsCreation.image_url)
    logger.info(f"Writer {message.from_user.id} set news description.")


@router.message(NewsCreation.image_url)
async def process_image_url(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "writer":
        await message.answer("🚫 Доступ запрещён!")
        return
    image_url = message.text if message.text.lower() != "нет" else ""
    await state.update_data(image_url=image_url)
    data = await state.get_data()

    response = (
        f"📰 Новая новость\n"
        f"Категория: {data['category'].capitalize()}\n"
        f"Заголовок: {data['title']}\n"
        f"Описание: {data['description']}\n"
    )
    if image_url:
        response += f"🖼 Картинка: {image_url}\n"
    response += "Подтвердить создание новости?"

    await message.answer(
        response,
        reply_markup=get_confirmation_keyboard("confirm_news", "cancel_news")
    )
    await state.set_state(NewsCreation.confirmation)
    logger.info(f"Writer {message.from_user.id} completed news creation form.")


@router.callback_query(lambda c: c.data == "confirm_news")
async def confirm_news(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if await get_user_role(user_id) != "writer":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return

    allowed, current_count, total_limit = await check_limit(user_id, "create_news")
    if not allowed:
        await callback.message.edit_text(
            f"⚠️ У вас закончились лимиты на создание новостей ({current_count}/{total_limit})!\n"
            "Хотите купить дополнительные лимиты? 💎",
            reply_markup=get_purchase_keyboard("create_news")
        )
        await callback.answer()
        logger.info(f"Writer {user_id} reached create limit: {current_count}/{total_limit}")
        return

    await increment_limit(user_id, "create_news")
    data = await state.get_data()
    news = {
        "category": data["category"],
        "title": data["title"],
        "description": data["description"],
        "image_url": data["image_url"],
        "author_id": callback.from_user.id,
        "source": "",
    }
    await add_pending_news(news)
    await callback.message.edit_text(
        "✅ Новость отправлена на проверку!",
        reply_markup=get_writer_panel()
    )
    await state.clear()
    await callback.answer()
    logger.info(f"Writer {callback.from_user.id} submitted news: {news['title']}")


@router.callback_query(lambda c: c.data == "cancel_news")
async def cancel_news(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🚫 Создание новости отменено.",
        reply_markup=get_writer_panel()
    )
    await state.clear()
    await callback.answer()
    logger.info(f"Writer {callback.from_user.id} canceled news creation.")


@router.callback_query(lambda c: c.data == "edit_news")
async def edit_news(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "writer":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    published, pending = await get_writer_news(callback.from_user.id)
    if not published and not pending:
        await callback.message.edit_text(
            "📭 У вас нет новостей для редактирования.",
            reply_markup=get_writer_panel()
        )
        await callback.answer()
        logger.info(f"Writer {callback.from_user.id} has no news to edit.")
        return

    await callback.message.edit_text(
        "📜 Выберите новость для редактирования:",
        reply_markup=get_writer_news_keyboard(published, pending)
    )
    await state.set_state(NewsEditing.selecting)
    await callback.answer()
    logger.info(f"Writer {callback.from_user.id} started editing news.")


@router.callback_query(lambda c: c.data.startswith("edit_published_"), NewsEditing.selecting)
async def edit_published_news(callback: CallbackQuery, state: FSMContext):
    news_id = int(callback.data.split("_")[2])
    news = await get_news_by_id(news_id)
    if not news or news["author_id"] != callback.from_user.id:
        await callback.message.edit_text(
            "❌ Новость не найдена или вы не её автор.",
            reply_markup=get_writer_panel()
        )
        await callback.answer()
        logger.warning(f"Writer {callback.from_user.id} tried to edit news ID {news_id} but failed.")
        return

    await state.update_data(news_id=news_id, is_published=True)
    await callback.message.edit_text(
        f"📋 Текущая категория: {news['category'].capitalize()}\nВыберите новую категорию:",
        reply_markup=get_categories_keyboard()
    )
    await state.set_state(NewsEditing.category)
    await callback.answer()
    logger.info(f"Writer {callback.from_user.id} started editing published news ID {news_id}.")


@router.callback_query(lambda c: c.data.startswith("edit_pending_"), NewsEditing.selecting)
async def edit_pending_news(callback: CallbackQuery, state: FSMContext):
    pending_id = int(callback.data.split("_")[2])
    pending_news = await get_pending_news()
    news = next((n for n in pending_news if n["pending_id"] == pending_id), None)
    if not news or news["author_id"] != callback.from_user.id:
        await callback.message.edit_text(
            "❌ Новость не найдена или вы не её автор.",
            reply_markup=get_writer_panel()
        )
        await callback.answer()
        logger.warning(f"Writer {callback.from_user.id} tried to edit pending news ID {pending_id} but failed.")
        return

    await state.update_data(pending_id=pending_id, is_published=False)
    await callback.message.edit_text(
        f"📋 Текущая категория: {news['category'].capitalize()}\nВыберите новую категорию:",
        reply_markup=get_categories_keyboard()
    )
    await state.set_state(NewsEditing.category)
    await callback.answer()
    logger.info(f"Writer {callback.from_user.id} started editing pending news ID {pending_id}.")


@router.callback_query(lambda c: c.data.startswith("category_"), NewsEditing.category)
async def edit_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("_")[1]
    await state.update_data(category=category)
    await callback.message.edit_text(
        "📝 Введите новый заголовок новости:"
    )
    await state.set_state(NewsEditing.title)
    await callback.answer()
    logger.info(f"Writer {callback.from_user.id} selected category {category} for editing news.")


@router.message(NewsEditing.title)
async def edit_title(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "writer":
        await message.answer("🚫 Доступ запрещён!")
        return
    await state.update_data(title=message.text)
    await message.answer(
        "📜 Введите новое описание новости:"
    )
    await state.set_state(NewsEditing.description)
    logger.info(f"Writer {message.from_user.id} set new title for editing news: {message.text}")


@router.message(NewsEditing.description)
async def edit_description(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "writer":
        await message.answer("🚫 Доступ запрещён!")
        return
    await state.update_data(description=message.text)
    await message.answer(
        "🖼 Введите новый URL картинки (или отправьте 'нет', чтобы пропустить):"
    )
    await state.set_state(NewsEditing.image_url)
    logger.info(f"Writer {message.from_user.id} set new description for editing news.")


@router.message(NewsEditing.image_url)
async def edit_image_url(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "writer":
        await message.answer("🚫 Доступ запрещён!")
        return
    image_url = message.text if message.text.lower() != "нет" else ""
    await state.update_data(image_url=image_url)
    data = await state.get_data()

    response = (
        f"📰 Обновлённая новость\n"
        f"Категория: {data['category'].capitalize()}\n"
        f"Заголовок: {data['title']}\n"
        f"Описание: {data['description']}\n"
    )
    if image_url:
        response += f"🖼 Картинка: {image_url}\n"
    response += "Подтвердить изменения?"

    await message.answer(
        response,
        reply_markup=get_confirmation_keyboard("confirm_edit", "cancel_edit")
    )
    await state.set_state(NewsEditing.confirmation)
    logger.info(f"Writer {message.from_user.id} completed news editing form.")


@router.callback_query(lambda c: c.data == "confirm_edit")
async def confirm_edit(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "writer":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return

    data = await state.get_data()
    news = {
        "category": data["category"],
        "title": data["title"],
        "description": data["description"],
        "image_url": data["image_url"],
    }

    if data.get("is_published"):
        news_id = data["news_id"]
        await update_news(news_id, news)
        logger.info(f"Writer {callback.from_user.id} updated published news ID {news_id}.")
    else:
        pending_id = data["pending_id"]
        await update_pending_news(pending_id, news)
        logger.info(f"Writer {callback.from_user.id} updated pending news ID {pending_id}.")

    await callback.message.edit_text(
        "✅ Изменения сохранены!",
        reply_markup=get_writer_panel()
    )
    await state.clear()
    await callback.answer()
    logger.info(f"Writer {callback.from_user.id} confirmed news edit.")


@router.callback_query(lambda c: c.data == "cancel_edit")
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🚫 Редактирование отменено.",
        reply_markup=get_writer_panel()
    )
    await state.clear()
    await callback.answer()
    logger.info(f"Writer {callback.from_user.id} canceled news editing.")


# Обработчики покупки лимитов
@router.callback_query(lambda c: c.data.startswith("buy_limits_"))
async def buy_limits(callback: CallbackQuery):
    action_type = callback.data.split("_")[2]
    action_text = "просмотров" if action_type == "view_news" else "постов"
    await callback.message.edit_text(
        f"💎 Покупка дополнительных {action_text}\nВыберите количество:",
        reply_markup=get_quantity_keyboard(action_type)
    )
    await callback.answer()
    logger.info(f"Writer {callback.from_user.id} started buying limits for {action_type}.")


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
        logger.error(f"Failed to create payment for writer {user_id}")
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
    logger.info(f"Writer {user_id} created payment {payment_id} for {quantity} {action_type}.")


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
        logger.info(f"Writer {user_id} successfully purchased {quantity} {action_type} for {cost}₽.")
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
        logger.info(f"Writer {user_id} checked payment {payment_id}, status: {payment['status']}.")