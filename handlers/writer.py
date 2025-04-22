from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.inline import get_writer_news_keyboard
from utils.database import get_user_role, insert_pending_news, get_writer_news, update_pending_news, delete_pending_news
from utils.logger import logger
from utils.database import check_limit, increment_limit
from aiogram.exceptions import TelegramBadRequest

router = Router()

class NewsCreation(StatesGroup):
    title = State()
    description = State()
    image_url = State()
    category = State()

class NewsEditing(StatesGroup):
    editing = State()

@router.callback_query(lambda c: c.data == "writer_panel")
async def writer_panel(callback: CallbackQuery):
    user_id = callback.from_user.id
    role = await get_user_role(user_id)
    if role != "writer":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return

    published, pending = await get_writer_news(user_id)
    if not published and not pending:
        new_text = "✍️ Панель писателя\nУ вас пока нет своих новостей 📭\nНажмите 'Создать новость' ниже, чтобы написать статью 👇"
    else:
        new_text = "✍️ Панель писателя\nВаши новости и действия 👇"

    new_keyboard = get_writer_news_keyboard(published, pending)

    try:
        await callback.message.edit_text(
            new_text,
            reply_markup=new_keyboard
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("ℹ️ Панель уже открыта.")
        else:
            logger.error(f"Error in writer_panel for user {user_id}: {str(e)}")
            raise
    except Exception as e:
        logger.error(f"Error in writer_panel for user {user_id}: {str(e)}")
        raise

    await callback.answer()
    logger.info(f"User {user_id} opened writer panel.")

@router.callback_query(lambda c: c.data == "create_news")
async def create_news(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    role = await get_user_role(user_id)
    if role != "admin":  # Пропускаем проверку лимитов для админов
        allowed, current_count, total_limit = await check_limit(user_id, "create_news")
        if not allowed:
            await callback.message.edit_text(
                f"⚠️ У вас закончились лимиты на создание новостей ({current_count}/{total_limit})!\n"
                "Хотите купить дополнительные посты? 💎",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💎 Купить дополнительные лимиты", callback_data="buy_limits_create_news")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="writer_panel")]
                ])
            )
            await callback.answer()
            logger.info(f"User {user_id} reached create limit: {current_count}/{total_limit}")
            return

    await state.clear()
    await callback.message.edit_text(
        "🖌 Создание новости\nВведите заголовок новости:"
    )
    await state.set_state(NewsCreation.title)
    current_state = await state.get_state()
    logger.info(f"User {callback.from_user.id} started creating news. Set state: {current_state}")
    await callback.answer()

@router.message(NewsCreation.title, F.text)
async def process_title(message: Message, state: FSMContext):
    current_state = await state.get_state()
    logger.info(f"Processing title for user {message.from_user.id}. Current state: {current_state}")
    await state.update_data(title=message.text)
    await message.answer("Введите описание новости:")
    await state.set_state(NewsCreation.description)
    new_state = await state.get_state()
    logger.info(f"User {message.from_user.id} set news title: {message.text}. New state: {new_state}")

@router.message(NewsCreation.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите URL картинки (или пропустите, отправив '-'):")
    await state.set_state(NewsCreation.image_url)
    logger.info(f"User {message.from_user.id} set news description: {message.text}")

@router.message(NewsCreation.image_url)
async def process_image_url(message: Message, state: FSMContext):
    image_url = None if message.text == "-" else message.text
    await state.update_data(image_url=image_url)
    await message.answer(
        "Выберите категорию новости:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="General", callback_data="category_general")],
            [InlineKeyboardButton(text="Business", callback_data="category_business")],
            [InlineKeyboardButton(text="Technology", callback_data="category_technology")],
            [InlineKeyboardButton(text="Entertainment", callback_data="category_entertainment")],
            [InlineKeyboardButton(text="Sports", callback_data="category_sports")],
        ])
    )
    await state.set_state(NewsCreation.category)
    logger.info(f"User {message.from_user.id} set news image URL: {image_url}")

@router.callback_query(lambda c: c.data.startswith("category_"), NewsCreation.category)
async def process_category(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    role = await get_user_role(user_id)
    if role != "admin":  # Пропускаем инкремент лимитов для админов
        await increment_limit(user_id, "create_news")

    category = callback.data.split("_")[1]
    data = await state.get_data()
    title = data["title"]
    description = data["description"]
    image_url = data["image_url"]

    pending_id = await insert_pending_news(user_id, title, description, image_url, category)
    published, pending = await get_writer_news(user_id)

    await callback.message.edit_text(
        f"✅ Новость отправлена на проверку! ID: {pending_id}\n",
        reply_markup=get_writer_news_keyboard(published, pending)
    )
    await state.clear()
    await callback.answer()
    logger.info(f"User {user_id} created pending news ID {pending_id} in category {category}.")

@router.callback_query(lambda c: c.data.startswith("edit_published_") or c.data.startswith("edit_pending_"))
async def edit_news(callback: CallbackQuery, state: FSMContext):
    news_type, news_id = callback.data.split("_")[1], int(callback.data.split("_")[2])
    published, pending = await get_writer_news(callback.from_user.id)
    news = None
    for item in (published if news_type == "published" else pending):
        if item[f"{news_type}_id"] == news_id:
            news = item
            break

    if not news:
        await callback.message.edit_text(
            "❌ Новость не найдена.",
            reply_markup=get_writer_news_keyboard(published, pending)
        )
        await callback.answer()
        return

    await state.update_data(news_id=news_id, news_type=news_type)
    await callback.message.edit_text(
        f"✍️ Редактирование новости (ID: {news_id})\n"
        f"Текущий заголовок: {news['title']}\n"
        f"Введите новый заголовок (или пропустите, отправив '-'):"
    )
    await state.set_state(NewsEditing.editing)
    await callback.answer()
    logger.info(f"User {callback.from_user.id} started editing {news_type} news ID {news_id}.")

@router.message(NewsEditing.editing)
async def process_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    news_id = data["news_id"]
    news_type = data["news_type"]
    title = message.text if message.text != "-" else None

    published, pending = await get_writer_news(message.from_user.id)
    news = None
    for item in (published if news_type == "published" else pending):
        if item[f"{news_type}_id"] == news_id:
            news = item
            break

    if not news:
        await message.answer(
            "❌ Новость не найдена.",
            reply_markup=get_writer_news_keyboard(published, pending)
        )
        await state.clear()
        return

    description = news["description"]
    image_url = news["image_url"]
    category = news["category"]

    if title:
        news["title"] = title
    await message.answer(
        f"Текущее описание: {description}\n"
        f"Введите новое описание (или пропустите, отправив '-'):"
    )
    await state.update_data(title=news["title"], description=description, image_url=image_url, category=category)
    await state.set_state(NewsEditing.editing)
    logger.info(f"User {message.from_user.id} updated title for {news_type} news ID {news_id}: {title}")

@router.message(NewsEditing.editing)
async def process_edit_description(message: Message, state: FSMContext):
    data = await state.get_data()
    description = message.text if message.text != "-" else data["description"]
    await state.update_data(description=description)
    await message.answer(
        f"Текущий URL картинки: {data['image_url']}\n"
        f"Введите новый URL (или пропустите, отправив '-'):"
    )
    await state.set_state(NewsEditing.editing)
    logger.info(f"User {message.from_user.id} updated description: {description}")

@router.message(NewsEditing.editing)
async def process_edit_image_url(message: Message, state: FSMContext):
    data = await state.get_data()
    image_url = message.text if message.text != "-" else data["image_url"]
    await state.update_data(image_url=image_url)
    await message.answer(
        "Выберите новую категорию новости:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="General", callback_data="edit_category_general")],
            [InlineKeyboardButton(text="Business", callback_data="edit_category_business")],
            [InlineKeyboardButton(text="Technology", callback_data="edit_category_technology")],
            [InlineKeyboardButton(text="Entertainment", callback_data="edit_category_entertainment")],
            [InlineKeyboardButton(text="Sports", callback_data="edit_category_sports")],
        ])
    )
    await state.set_state(NewsEditing.editing)
    logger.info(f"User {message.from_user.id} updated image URL: {image_url}")

@router.callback_query(lambda c: c.data.startswith("edit_category_"), NewsEditing.editing)
async def process_edit_category(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    news_id = data["news_id"]
    news_type = data["news_type"]
    category = callback.data.split("_")[2]

    await update_pending_news(
        news_id=news_id,
        title=data["title"],
        description=data["description"],
        image_url=data["image_url"],
        category=category,
        is_published=(news_type == "published")
    )

    published, pending = await get_writer_news(callback.from_user.id)
    await callback.message.edit_text(
        f"✅ Новость ID {news_id} обновлена!",
        reply_markup=get_writer_news_keyboard(published, pending)
    )
    await state.clear()
    await callback.answer()
    logger.info(f"User {callback.from_user.id} updated {news_type} news ID {news_id} in category {category}.")

@router.callback_query(lambda c: c.data.startswith("delete_published_") or c.data.startswith("delete_pending_"))
async def delete_news(callback: CallbackQuery):
    news_type, news_id = callback.data.split("_")[1], int(callback.data.split("_")[2])
    await delete_pending_news(news_id, is_published=(news_type == "published"))
    published, pending = await get_writer_news(callback.from_user.id)

    await callback.message.edit_text(
        f"🗑 Новость ID {news_id} удалена!",
        reply_markup=get_writer_news_keyboard(published, pending)
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} deleted {news_type} news ID {news_id}.")