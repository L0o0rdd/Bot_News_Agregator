from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.database import get_user_role, set_user_role, get_users_by_role, get_pending_news, approve_news, reject_news, get_subscribers
from utils.logger import logger
from keyboards.inline import get_admin_keyboard, get_role_management_keyboard, get_role_selection_keyboard, get_pending_news_keyboard
from aiogram.exceptions import TelegramBadRequest

router = Router()

@router.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    user_id = callback.from_user.id
    role = await get_user_role(user_id)
    if role not in ["admin", "manager"]:
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return

    new_text = "🛠 Панель управления\nВыберите действие:"
    new_keyboard = get_admin_keyboard()

    try:
        await callback.message.edit_text(new_text, reply_markup=new_keyboard)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("ℹ️ Панель уже открыта.")
        else:
            logger.error(f"Error in admin_panel for user {user_id}: {str(e)}")
            raise
    except Exception as e:
        logger.error(f"Error in admin_panel for user {user_id}: {str(e)}")
        raise

    await callback.answer()
    logger.info(f"User {user_id} opened admin panel.")

@router.callback_query(lambda c: c.data == "review_news")
async def review_news(callback: CallbackQuery):
    user_id = callback.from_user.id
    role = await get_user_role(user_id)
    if role not in ["admin", "manager"]:
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return

    news = await get_pending_news()
    if not news:
        await callback.message.edit_text(
            "📭 Нет новостей на проверку.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
            ])
        )
        await callback.answer()
        return

    new_text = "📋 Проверка новостей\nВыберите новость для проверки:"
    new_keyboard = get_pending_news_keyboard(news)

    await callback.message.edit_text(new_text, reply_markup=new_keyboard)
    await callback.answer()
    logger.info(f"User {user_id} opened news review panel.")

@router.callback_query(lambda c: c.data.startswith("view_pending_"))
async def view_pending_news(callback: CallbackQuery):
    user_id = callback.from_user.id
    role = await get_user_role(user_id)
    if role not in ["admin", "manager"]:
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return

    pending_id = int(callback.data.split("_")[2])
    news = await get_pending_news()
    selected_news = None
    for n in news:
        if n["pending_id"] == pending_id:
            selected_news = n
            break

    if not selected_news:
        await callback.message.edit_text(
            "❌ Новость не найдена.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="review_news")]
            ])
        )
        await callback.answer()
        return

    new_text = (
        f"📰 Новость на проверке (ID: {pending_id})\n"
        f"Категория: {selected_news['category']}\n"
        f"Заголовок: {selected_news['title']}\n"
        f"Описание: {selected_news['description']}\n"
        f"URL картинки: {selected_news['image_url'] if selected_news['image_url'] else 'Нет'}\n"
        f"Автор: {'RSS' if selected_news['writer_id'] == 0 else selected_news['writer_id']}\n"
        f"Создано: {selected_news['created_at']}"
    )
    new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{pending_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{pending_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="review_news")]
    ])

    await callback.message.edit_text(new_text, reply_markup=new_keyboard)
    await callback.answer()
    logger.info(f"User {user_id} viewed pending news ID {pending_id}.")

@router.callback_query(lambda c: c.data.startswith("approve_"))
async def approve_news_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    role = await get_user_role(user_id)
    if role not in ["admin", "manager"]:
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return

    pending_id = int(callback.data.split("_")[1])
    news_id = await approve_news(pending_id)
    if news_id is None:
        await callback.message.edit_text(
            "❌ Новость не найдена.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="review_news")]
            ])
        )
        await callback.answer()
        return

    news = await get_pending_news()
    new_text = f"✅ Новость ID {pending_id} одобрена! Опубликована под ID {news_id}."
    new_keyboard = get_pending_news_keyboard(news)

    await callback.message.edit_text(new_text, reply_markup=new_keyboard)
    await callback.answer()

    subscribers = await get_subscribers(news[0]["category"])
    for subscriber in subscribers:
        try:
            await callback.message.bot.send_message(
                subscriber,
                f"📰 Новая новость в категории {news[0]['category'].capitalize()}!\n"
                f"Заголовок: {news[0]['title']}\n"
                f"Описание: {news[0]['description']}"
            )
        except Exception as e:
            logger.error(f"Error notifying subscriber {subscriber}: {str(e)}")

    logger.info(f"User {user_id} approved news ID {pending_id}, published as {news_id}.")

@router.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_news_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    role = await get_user_role(user_id)
    if role not in ["admin", "manager"]:
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return

    pending_id = int(callback.data.split("_")[1])
    writer_id = await reject_news(pending_id)
    if writer_id is None:
        await callback.message.edit_text(
            "❌ Новость не найдена.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="review_news")]
            ])
        )
        await callback.answer()
        return

    news = await get_pending_news()
    new_text = f"❌ Новость ID {pending_id} отклонена."
    new_keyboard = get_pending_news_keyboard(news)

    await callback.message.edit_text(new_text, reply_markup=new_keyboard)
    await callback.answer()
    logger.info(f"User {user_id} rejected news ID {pending_id}.")

@router.callback_query(lambda c: c.data == "manage_roles")
async def manage_roles(callback: CallbackQuery):
    user_id = callback.from_user.id
    role = await get_user_role(user_id)
    if role != "admin":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return

    users = await get_users_by_role("writer")
    new_text = "👥 Управление ролями\nВыберите пользователя:"
    new_keyboard = get_role_management_keyboard(users)

    await callback.message.edit_text(new_text, reply_markup=new_keyboard)
    await callback.answer()
    logger.info(f"User {user_id} opened role management panel.")

@router.callback_query(lambda c: c.data.startswith("set_role_"))
async def set_role(callback: CallbackQuery):
    user_id = callback.from_user.id
    role = await get_user_role(user_id)
    if role != "admin":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return

    target_user_id = int(callback.data.split("_")[2])
    new_text = f"👤 Пользователь {target_user_id}\nВыберите роль:"
    new_keyboard = get_role_selection_keyboard(target_user_id)

    await callback.message.edit_text(new_text, reply_markup=new_keyboard)
    await callback.answer()
    logger.info(f"User {user_id} started role selection for user {target_user_id}.")

@router.callback_query(lambda c: c.data.startswith("role_"))
async def assign_role(callback: CallbackQuery):
    user_id = callback.from_user.id
    role = await get_user_role(user_id)
    if role != "admin":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return

    data = callback.data.split("_")
    new_role = data[1]
    target_user_id = int(data[2])

    await set_user_role(target_user_id, new_role)
    users = await get_users_by_role("writer")
    new_text = f"✅ Роль пользователя {target_user_id} изменена на {new_role}."
    new_keyboard = get_role_management_keyboard(users)

    await callback.message.edit_text(new_text, reply_markup=new_keyboard)
    await callback.answer()
    logger.info(f"User {user_id} set role {new_role} for user {target_user_id}.")