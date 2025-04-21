import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.inline import get_admin_panel, get_user_selection_keyboard, get_confirmation_keyboard, \
    get_rss_management_keyboard
from utils.database import get_user_role, set_user_role, get_pending_news, approve_news, reject_news, remove_user_role, \
    get_sources
from utils.logger import logger

router = Router()

class AdminActions(StatesGroup):
    waiting_for_user_id = State()
    reviewing_news = State()

@router.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛠 Админ-панель\nВыбери действие ниже 👇",
        reply_markup=get_admin_panel()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} opened admin panel.")

@router.callback_query(lambda c: c.data == "assign_manager")
async def assign_manager(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "👤 Введите ID пользователя для назначения роли менеджера:"
    )
    await state.set_state(AdminActions.waiting_for_user_id)
    await state.update_data(action="assign_manager")
    await callback.answer()
    logger.info(f"User {callback.from_user.id} started assigning manager role.")

@router.callback_query(lambda c: c.data == "assign_writer")
async def assign_writer(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✍️ Введите ID пользователя для назначения роли писателя:"
    )
    await state.set_state(AdminActions.waiting_for_user_id)
    await state.update_data(action="assign_writer")
    await callback.answer()
    logger.info(f"User {callback.from_user.id} started assigning writer role.")

@router.message(AdminActions.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректный ID пользователя (число).",
            reply_markup=get_admin_panel()
        )
        await state.clear()
        return

    data = await state.get_data()
    action = data["action"]
    role = "manager" if action == "assign_manager" else "writer"

    current_role = await get_user_role(user_id)
    if current_role == role:
        await message.answer(
            f"⚠️ Пользователь с ID {user_id} уже имеет роль {role.capitalize()}.",
            reply_markup=get_admin_panel()
        )
        await state.clear()
        return

    await set_user_role(user_id, role)
    await message.answer(
        f"✅ Пользователь с ID {user_id} назначен как {role.capitalize()}!",
        reply_markup=get_admin_panel()
    )
    await state.clear()
    logger.info(f"User {message.from_user.id} assigned role {role} to user {user_id}.")

@router.callback_query(lambda c: c.data == "remove_manager")
async def remove_manager(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🗑 Введите ID пользователя для удаления роли менеджера:"
    )
    await state.set_state(AdminActions.waiting_for_user_id)
    await state.update_data(action="remove_manager")
    await callback.answer()
    logger.info(f"User {callback.from_user.id} started removing manager role.")

@router.callback_query(lambda c: c.data == "remove_writer")
async def remove_writer(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🗑 Введите ID пользователя для удаления роли писателя:"
    )
    await state.set_state(AdminActions.waiting_for_user_id)
    await state.update_data(action="remove_writer")
    await callback.answer()
    logger.info(f"User {callback.from_user.id} started removing writer role.")

@router.message(AdminActions.waiting_for_user_id)
async def process_remove_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректный ID пользователя (число).",
            reply_markup=get_admin_panel()
        )
        await state.clear()
        return

    data = await state.get_data()
    action = data["action"]
    role = "manager" if action == "remove_manager" else "writer"

    if await remove_user_role(user_id, role):
        await message.answer(
            f"✅ Роль {role.capitalize()} у пользователя с ID {user_id} удалена!",
            reply_markup=get_admin_panel()
        )
    else:
        await message.answer(
            f"⚠️ Пользователь с ID {user_id} не имеет роль {role.capitalize()}.",
            reply_markup=get_admin_panel()
        )
    await state.clear()
    logger.info(f"User {message.from_user.id} removed role {role} from user {user_id}.")

@router.callback_query(lambda c: c.data == "review_news")
async def review_news(callback: CallbackQuery, state: FSMContext):
    pending_news = await get_pending_news()
    if not pending_news:
        await callback.message.edit_text(
            "📭 Нет новостей на проверке.",
            reply_markup=get_admin_panel()
        )
        await callback.answer()
        return

    await state.update_data(pending_news=pending_news, current_index=0)
    news_item = pending_news[0]
    response = (
        f"📰 Новость на проверке (ID: {news_item['pending_id']})\n"
        f"Категория: {news_item['category'].capitalize()}\n"
        f"Заголовок: {news_item['title']}\n"
        f"Описание: {news_item['description']}\n"
    )
    if news_item['image_url']:
        response += f"🖼 Картинка: {news_item['image_url']}\n"
    response += f"Автор: ID {news_item['writer_id']}\n"
    response += f"Создана: {news_item['created_at']}\n"

    kb = [
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_news_{news_item['pending_id']}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_news_{news_item['pending_id']}")],
    ]
    if len(pending_news) > 1:
        kb.append([InlineKeyboardButton(text="➡️ Следующая", callback_data="next_pending_0")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])

    await callback.message.edit_text(
        response,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await state.set_state(AdminActions.reviewing_news)
    await callback.answer()
    logger.info(f"User {callback.from_user.id} started reviewing pending news.")

@router.callback_query(lambda c: c.data.startswith("next_pending_"), AdminActions.reviewing_news)
async def next_pending_news(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pending_news = data.get("pending_news", [])
    current_index = int(callback.data.split("_")[2])
    current_index = (current_index + 1) % len(pending_news)

    await state.update_data(current_index=current_index)
    news_item = pending_news[current_index]
    response = (
        f"📰 Новость на проверке (ID: {news_item['pending_id']})\n"
        f"Категория: {news_item['category'].capitalize()}\n"
        f"Заголовок: {news_item['title']}\n"
        f"Описание: {news_item['description']}\n"
    )
    if news_item['image_url']:
        response += f"🖼 Картинка: {news_item['image_url']}\n"
    response += f"Автор: ID {news_item['writer_id']}\n"
    response += f"Создана: {news_item['created_at']}\n"

    kb = [
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_news_{news_item['pending_id']}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_news_{news_item['pending_id']}")],
    ]
    if len(pending_news) > 1:
        kb.append([
            InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"next_pending_{(current_index - 1) % len(pending_news)}"),
            InlineKeyboardButton(text="➡️ Следующая", callback_data=f"next_pending_{(current_index + 1) % len(pending_news)}")
        ])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])

    await callback.message.edit_text(
        response,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} navigated to pending news ID {news_item['pending_id']}.")

@router.callback_query(lambda c: c.data.startswith("approve_news_"), AdminActions.reviewing_news)
async def approve_news_handler(callback: CallbackQuery, state: FSMContext):
    pending_id = int(callback.data.split("_")[2])
    news_id = await approve_news(pending_id)
    if news_id is None:
        await callback.message.edit_text(
            "❌ Новость не найдена.",
            reply_markup=get_admin_panel()
        )
        await state.clear()
        await callback.answer()
        return

    pending_news = await get_pending_news()
    if not pending_news:
        await callback.message.edit_text(
            "📭 Больше нет новостей на проверке.",
            reply_markup=get_admin_panel()
        )
        await state.clear()
    else:
        await state.update_data(pending_news=pending_news, current_index=0)
        news_item = pending_news[0]
        response = (
            f"📰 Новость на проверке (ID: {news_item['pending_id']})\n"
            f"Категория: {news_item['category'].capitalize()}\n"
            f"Заголовок: {news_item['title']}\n"
            f"Описание: {news_item['description']}\n"
        )
        if news_item['image_url']:
            response += f"🖼 Картинка: {news_item['image_url']}\n"
        response += f"Автор: ID {news_item['writer_id']}\n"
        response += f"Создана: {news_item['created_at']}\n"

        kb = [
            [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_news_{news_item['pending_id']}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_news_{news_item['pending_id']}")],
        ]
        if len(pending_news) > 1:
            kb.append([InlineKeyboardButton(text="➡️ Следующая", callback_data="next_pending_0")])
        kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])

        await callback.message.edit_text(
            response,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    await callback.answer(f"✅ Новость ID {pending_id} одобрена! Опубликована как ID {news_id}.")
    logger.info(f"User {callback.from_user.id} approved news ID {pending_id} as news ID {news_id}.")

@router.callback_query(lambda c: c.data.startswith("reject_news_"), AdminActions.reviewing_news)
async def reject_news_handler(callback: CallbackQuery, state: FSMContext):
    pending_id = int(callback.data.split("_")[2])
    await reject_news(pending_id)

    pending_news = await get_pending_news()
    if not pending_news:
        await callback.message.edit_text(
            "📭 Больше нет новостей на проверке.",
            reply_markup=get_admin_panel()
        )
        await state.clear()
    else:
        await state.update_data(pending_news=pending_news, current_index=0)
        news_item = pending_news[0]
        response = (
            f"📰 Новость на проверке (ID: {news_item['pending_id']})\n"
            f"Категория: {news_item['category'].capitalize()}\n"
            f"Заголовок: {news_item['title']}\n"
            f"Описание: {news_item['description']}\n"
        )
        if news_item['image_url']:
            response += f"🖼 Картинка: {news_item['image_url']}\n"
        response += f"Автор: ID {news_item['writer_id']}\n"
        response += f"Создана: {news_item['created_at']}\n"

        kb = [
            [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_news_{news_item['pending_id']}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_news_{news_item['pending_id']}")],
        ]
        if len(pending_news) > 1:
            kb.append([InlineKeyboardButton(text="➡️ Следующая", callback_data="next_pending_0")])
        kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])

        await callback.message.edit_text(
            response,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    await callback.answer(f"❌ Новость ID {pending_id} отклонена.")
    logger.info(f"User {callback.from_user.id} rejected news ID {pending_id}.")

@router.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    async with aiosqlite.connect("news_bot.db") as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM news")
        total_news = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM pending_news")
        pending_news = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM sources")
        total_sources = (await cursor.fetchone())[0]

    response = (
        "📊 Статистика\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📰 Всего новостей: {total_news}\n"
        f"⏳ Новостей на проверке: {pending_news}\n"
        f"📡 Всего источников: {total_sources}\n"
    )

    await callback.message.edit_text(
        response,
        reply_markup=get_admin_panel()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} viewed admin stats.")

@router.callback_query(lambda c: c.data == "manage_rss")
async def manage_rss(callback: CallbackQuery):
    sources = await get_sources()
    if not sources:
        await callback.message.edit_text(
            "📭 Источников пока нет.",
            reply_markup=get_admin_panel()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "📡 Управление RSS-лентами:",
        reply_markup=get_rss_management_keyboard(sources)
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} opened RSS management.")