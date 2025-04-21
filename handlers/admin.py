from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from config.config import ADMIN_ID, BOT_TOKEN
from keyboards.inline import get_admin_panel, get_confirmation_keyboard, get_user_selection_keyboard, \
    get_rss_management_keyboard, get_manager_panel
from utils.database import get_user_role, set_user_role, get_pending_news, approve_news, reject_news, remove_user_role, \
    get_users_by_role, clear_old_news, get_sources, toggle_source, get_admin_stats, get_news_by_id, get_subscribers
from utils.logger import logger

router = Router()


class AssignRole(StatesGroup):
    waiting_for_id = State()
    waiting_for_confirmation = State()


class RemoveRole(StatesGroup):
    waiting_for_id = State()
    waiting_for_reason = State()
    waiting_for_confirmation = State()


class ReviewNews(StatesGroup):
    waiting_for_action = State()


@router.message(Command("clear_old_news"))
async def clear_old_news_cmd(message: Message):
    if await get_user_role(message.from_user.id) != "admin":
        await message.answer("🚫 Доступ запрещён!")
        return
    await clear_old_news(days=30)
    await message.answer("🗑 Старые новости (старше 30 дней) перемещены в архив.")
    logger.info(f"Admin {message.from_user.id} cleared old news.")


@router.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "admin":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    await callback.message.edit_text(
        "🛠 Админ-панель\n"
        "Выберите действие 👇",
        reply_markup=get_admin_panel()
    )
    await callback.answer()
    logger.info(f"Admin {callback.from_user.id} opened admin panel.")


@router.callback_query(lambda c: c.data == "assign_manager")
async def assign_manager(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "admin":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    await callback.message.edit_text(
        "👤 Введите ID пользователя, которого хотите назначить менеджером:",
        reply_markup=None
    )
    await state.set_state(AssignRole.waiting_for_id)
    await state.update_data(role="manager")
    await callback.answer()
    logger.info(f"Admin {callback.from_user.id} started assigning manager role.")


@router.callback_query(lambda c: c.data == "assign_writer")
async def assign_writer(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "admin":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    await callback.message.edit_text(
        "✍️ Введите ID пользователя, которого хотите назначить писателем:",
        reply_markup=None
    )
    await state.set_state(AssignRole.waiting_for_id)
    await state.update_data(role="writer")
    await callback.answer()
    logger.info(f"Admin {callback.from_user.id} started assigning writer role.")


@router.message(AssignRole.waiting_for_id)
async def process_role_id(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "admin":
        await message.answer("🚫 Доступ запрещён!")
        return
    try:
        user_id = int(message.text)
        current_role = await get_user_role(user_id)
        data = await state.get_data()
        new_role = data["role"]

        if current_role == new_role:
            await message.answer(
                f"🚫 Этот пользователь уже {new_role}!",
                reply_markup=get_admin_panel()
            )
            await state.clear()
            logger.warning(
                f"Admin {message.from_user.id} tried to assign role {new_role} to user {user_id}, but user already has this role.")
            return

        await state.update_data(user_id=user_id)
        await message.answer(
            f"ℹ️ Пользователь с ID {user_id} имеет роль: {current_role}\n"
            f"Назначить роль {new_role}?",
            reply_markup=get_confirmation_keyboard("confirm_role", "cancel_role")
        )
        await state.set_state(AssignRole.waiting_for_confirmation)
        logger.info(f"Admin {message.from_user.id} selected user {user_id} to assign role {new_role}.")
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректный ID (целое число).",
            reply_markup=get_admin_panel()
        )
        await state.clear()
        logger.error(f"Admin {message.from_user.id} entered invalid user ID: {message.text}")


@router.callback_query(lambda c: c.data == "confirm_role")
async def confirm_role(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "admin":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    data = await state.get_data()
    user_id = data["user_id"]
    role = data["role"]
    await set_user_role(user_id, role)
    await callback.message.edit_text(
        f"✅ Пользователь с ID {user_id} назначен {role}!",
        reply_markup=get_admin_panel()
    )
    try:
        await callback.message.bot.send_message(
            user_id,
            f"🎉 Вам назначена роль {role}!"
        )
    except:
        logger.warning(f"Failed to notify user {user_id} about new role {role}.")
    await state.clear()
    await callback.answer()
    logger.info(f"Admin {callback.from_user.id} assigned role {role} to user {user_id}.")


@router.callback_query(lambda c: c.data == "cancel_role")
async def cancel_role(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🚫 Назначение роли отменено.",
        reply_markup=get_admin_panel()
    )
    await state.clear()
    await callback.answer()
    logger.info(f"Admin {callback.from_user.id} canceled role assignment.")


@router.callback_query(lambda c: c.data == "remove_manager")
async def remove_manager(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "admin":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    managers = await get_users_by_role("manager")
    if not managers:
        await callback.message.edit_text(
            "📭 Нет менеджеров для удаления.",
            reply_markup=get_admin_panel()
        )
        await callback.answer()
        logger.info(f"Admin {callback.from_user.id} tried to remove manager, but no managers found.")
        return
    logger.info(f"Managers list for removal: {managers}")
    await callback.message.edit_text(
        "👤 Выберите менеджера для удаления:",
        reply_markup=get_user_selection_keyboard(managers, "remove_manager")
    )
    await state.set_state(RemoveRole.waiting_for_id)
    await callback.answer()
    logger.info(f"Admin {callback.from_user.id} started removing manager.")


@router.callback_query(lambda c: c.data == "remove_writer")
async def remove_writer(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) not in ["admin", "manager"]:
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    writers = await get_users_by_role("writer")
    if not writers:
        await callback.message.edit_text(
            "📭 Нет писателей для удаления.",
            reply_markup=get_admin_panel() if await get_user_role(
                callback.from_user.id) == "admin" else get_manager_panel()
        )
        await callback.answer()
        logger.info(f"User {callback.from_user.id} tried to remove writer, but no writers found.")
        return
    logger.info(f"Writers list for removal: {writers}")
    await callback.message.edit_text(
        "✍️ Выберите писателя для удаления:",
        reply_markup=get_user_selection_keyboard(writers, "remove_writer")
    )
    await state.set_state(RemoveRole.waiting_for_id)
    await callback.answer()
    logger.info(f"User {callback.from_user.id} started removing writer.")


@router.callback_query(lambda c: c.data.startswith("select_user_"), RemoveRole.waiting_for_id)
async def process_remove_user_id(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Callback data: {callback.data}")
    parts = callback.data.split("_")
    if len(parts) < 5 or not parts[-1].isdigit():
        await callback.message.edit_text(
            "❌ Ошибка: некорректный выбор пользователя.",
            reply_markup=get_admin_panel() if await get_user_role(
                callback.from_user.id) == "admin" else get_manager_panel()
        )
        await callback.answer()
        logger.error(f"User {callback.from_user.id} provided invalid callback data: {callback.data}")
        return
    user_id = int(parts[-1])
    await state.update_data(user_id=user_id)
    await callback.message.edit_text(
        f"ℹ️ Вы выбрали пользователя с ID {user_id} для удаления роли.\n"
        "Укажите причину удаления (или напишите 'нет', чтобы пропустить):",
        reply_markup=None
    )
    await state.set_state(RemoveRole.waiting_for_reason)
    await callback.answer()
    logger.info(f"User {callback.from_user.id} selected user {user_id} for role removal.")


@router.message(RemoveRole.waiting_for_reason)
async def process_remove_reason(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) not in ["admin", "manager"]:
        await message.answer("🚫 Доступ запрещён!")
        return
    reason = message.text if message.text.lower() != "нет" else "Причина не указана"
    data = await state.get_data()
    user_id = data["user_id"]
    await state.update_data(reason=reason)
    await message.answer(
        f"ℹ️ Удалить роль у пользователя с ID {user_id}?\n"
        f"Причина: {reason}\n"
        "Подтвердите действие:",
        reply_markup=get_confirmation_keyboard("confirm_remove_role", "cancel_remove_role")
    )
    await state.set_state(RemoveRole.waiting_for_confirmation)
    logger.info(f"User {message.from_user.id} provided reason for role removal: {reason}")


@router.callback_query(lambda c: c.data == "confirm_remove_role")
async def confirm_remove_role(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) not in ["admin", "manager"]:
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    data = await state.get_data()
    user_id = data["user_id"]
    reason = data["reason"]
    await remove_user_role(user_id)
    await callback.message.edit_text(
        f"✅ Роль пользователя с ID {user_id} удалена!\nПричина: {reason}",
        reply_markup=get_admin_panel() if await get_user_role(callback.from_user.id) == "admin" else get_manager_panel()
    )
    try:
        await callback.message.bot.send_message(
            user_id,
            f"⚠️ Ваша роль была удалена.\nПричина: {reason}"
        )
    except:
        logger.warning(f"Failed to notify user {user_id} about role removal.")
    await state.clear()
    await callback.answer()
    logger.info(f"User {callback.from_user.id} removed role from user {user_id} with reason: {reason}")


@router.callback_query(lambda c: c.data == "cancel_remove_role")
async def cancel_remove_role(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🚫 Удаление роли отменено.",
        reply_markup=get_admin_panel() if await get_user_role(callback.from_user.id) == "admin" else get_manager_panel()
    )
    await state.clear()
    await callback.answer()
    logger.info(f"User {callback.from_user.id} canceled role removal.")


@router.callback_query(lambda c: c.data == "review_news")
async def review_news(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) not in ["admin", "manager"]:
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    pending_news = await get_pending_news()
    if not pending_news:
        await callback.message.edit_text(
            "📭 Нет новостей на проверку.",
            reply_markup=get_admin_panel() if await get_user_role(
                callback.from_user.id) == "admin" else get_manager_panel()
        )
        await callback.answer()
        logger.info(f"User {callback.from_user.id} tried to review news, but no pending news found.")
        return

    news = pending_news[0]
    response = (
        f"📰 Новость на проверку (ID: {news['pending_id']})\n"
        f"Категория: {news['category'].capitalize()}\n"
        f"Заголовок: {news['title']}\n"
        f"Описание: {news['description']}\n"
    )
    if news['image_url']:
        response += f"🖼 Картинка: {news['image_url']}\n"
    response += f"Источник: {news['source']}\n"
    response += f"Автор: ID {news['author_id']}\n"
    response += f"Дата: {news['submitted_at']}\n\n"
    response += "Выберите действие:"

    await state.update_data(pending_news=pending_news, current_index=0)
    await callback.message.edit_text(
        response,
        reply_markup=get_confirmation_keyboard(f"approve_news_{news['pending_id']}",
                                               f"reject_news_{news['pending_id']}")
    )
    await state.set_state(ReviewNews.waiting_for_action)
    await callback.answer()
    logger.info(f"User {callback.from_user.id} started reviewing news ID {news['pending_id']}.")


@router.callback_query(lambda c: c.data.startswith("approve_news_"))
async def approve_news_action(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) not in ["admin", "manager"]:
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    pending_id = int(callback.data.split("_")[2])
    author_id = await approve_news(pending_id)
    if author_id:
        try:
            await callback.message.bot.send_message(
                author_id,
                f"✅ Ваша новость (ID: {pending_id}) одобрена!"
            )
        except:
            logger.warning(f"Failed to notify author {author_id} about news approval.")

        # Получаем информацию о новости для уведомления подписчиков
        news = await get_news_by_id(pending_id)
        if news:
            subscribers = await get_subscribers(news["category"])
            notification = (
                f"🔔 Новая новость в категории {news['category'].capitalize()}!\n"
                f"Заголовок: {news['title']}\n"
                f"Описание: {news['description']}\n"
            )
            if news['image_url']:
                notification += f"🖼 Картинка: {news['image_url']}\n"
            notification += f"Источник: {news['source']}\n"
            notification += f"Опубликовано: {news['published_at']}"

            for user_id in subscribers:
                try:
                    await callback.message.bot.send_message(
                        user_id,
                        notification
                    )
                    logger.info(f"Notified user {user_id} about new news in category {news['category']}.")
                except:
                    logger.warning(f"Failed to notify user {user_id} about new news in category {news['category']}.")

    data = await state.get_data()
    pending_news = data.get("pending_news", [])
    current_index = data.get("current_index", 0)

    if current_index + 1 < len(pending_news):
        news = pending_news[current_index + 1]
        response = (
            f"📰 Новость на проверку (ID: {news['pending_id']})\n"
            f"Категория: {news['category'].capitalize()}\n"
            f"Заголовок: {news['title']}\n"
            f"Описание: {news['description']}\n"
        )
        if news['image_url']:
            response += f"🖼 Картинка: {news['image_url']}\n"
        response += f"Источник: {news['source']}\n"
        response += f"Автор: ID {news['author_id']}\n"
        response += f"Дата: {news['submitted_at']}\n\n"
        response += "Выберите действие:"

        await state.update_data(current_index=current_index + 1)
        await callback.message.edit_text(
            response,
            reply_markup=get_confirmation_keyboard(f"approve_news_{news['pending_id']}",
                                                   f"reject_news_{news['pending_id']}")
        )
    else:
        await callback.message.edit_text(
            "✅ Все новости проверены!",
            reply_markup=get_admin_panel() if await get_user_role(
                callback.from_user.id) == "admin" else get_manager_panel()
        )
        await state.clear()
    await callback.answer("✅ Новость одобрена!")
    logger.info(f"User {callback.from_user.id} approved news ID {pending_id}.")


@router.callback_query(lambda c: c.data.startswith("reject_news_"))
async def reject_news_action(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) not in ["admin", "manager"]:
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    pending_id = int(callback.data.split("_")[2])
    author_id = await reject_news(pending_id)
    if author_id:
        try:
            await callback.message.bot.send_message(
                author_id,
                f"❌ Ваша новость (ID: {pending_id}) отклонена."
            )
        except:
            logger.warning(f"Failed to notify author {author_id} about news rejection.")

    data = await state.get_data()
    pending_news = data.get("pending_news", [])
    current_index = data.get("current_index", 0)

    if current_index + 1 < len(pending_news):
        news = pending_news[current_index + 1]
        response = (
            f"📰 Новость на проверку (ID: {news['pending_id']})\n"
            f"Категория: {news['category'].capitalize()}\n"
            f"Заголовок: {news['title']}\n"
            f"Описание: {news['description']}\n"
        )
        if news['image_url']:
            response += f"🖼 Картинка: {news['image_url']}\n"
        response += f"Источник: {news['source']}\n"
        response += f"Автор: ID {news['author_id']}\n"
        response += f"Дата: {news['submitted_at']}\n\n"
        response += "Выберите действие:"

        await state.update_data(current_index=current_index + 1)
        await callback.message.edit_text(
            response,
            reply_markup=get_confirmation_keyboard(f"approve_news_{news['pending_id']}",
                                                   f"reject_news_{news['pending_id']}")
        )
    else:
        await callback.message.edit_text(
            "✅ Все новости проверены!",
            reply_markup=get_admin_panel() if await get_user_role(
                callback.from_user.id) == "admin" else get_manager_panel()
        )
        await state.clear()
    await callback.answer("❌ Новость отклонена!")
    logger.info(f"User {callback.from_user.id} rejected news ID {pending_id}.")


@router.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "admin":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    stats = await get_admin_stats()
    response = "📊 Статистика бота\n\n"
    response += f"👥 Всего пользователей: {stats['total_users']}\n"
    response += f"👤 Менеджеров: {stats['managers']}\n"
    response += f"✍️ Писателей: {stats['writers']}\n\n"
    response += "📰 Новости по категориям:\n"
    for category, count in stats['news_by_category'].items():
        response += f"  - {category.capitalize()}: {count}\n"
    response += f"\n👍 Всего лайков: {stats['total_likes']}\n"
    response += f"👎 Всего дизлайков: {stats['total_dislikes']}\n\n"
    response += "🏆 Топ-5 новостей по рейтингу:\n"
    for news in stats['top_news']:
        response += f"- ID {news['news_id']}: {news['title']} (Рейтинг: {news['rating']})\n"

    await callback.message.edit_text(
        response,
        reply_markup=get_admin_panel()
    )
    await callback.answer()
    logger.info(f"Admin {callback.from_user.id} viewed bot statistics.")


@router.callback_query(lambda c: c.data == "manage_rss")
async def manage_rss(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "admin":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    sources = await get_sources()
    if not sources:
        await callback.message.edit_text(
            "📭 Нет источников для управления.",
            reply_markup=get_admin_panel()
        )
        await callback.answer()
        logger.info(f"Admin {callback.from_user.id} tried to manage RSS, but no sources found.")
        return

    await callback.message.edit_text(
        "📡 Управление RSS-лентами\nНажмите на источник, чтобы включить/выключить:",
        reply_markup=get_rss_management_keyboard(sources)
    )
    await callback.answer()
    logger.info(f"Admin {callback.from_user.id} opened RSS management.")


@router.callback_query(lambda c: c.data.startswith("toggle_source_"))
async def toggle_rss_source(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "admin":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    source_id = int(callback.data.split("_")[2])
    if await toggle_source(source_id):
        sources = await get_sources()
        await callback.message.edit_text(
            "📡 Управление RSS-лентами\nНажмите на источник, чтобы включить/выключить:",
            reply_markup=get_rss_management_keyboard(sources)
        )
        await callback.answer("✅ Статус источника изменён!")
        logger.info(f"Admin {callback.from_user.id} toggled RSS source ID {source_id}.")
    else:
        await callback.answer("❌ Ошибка при изменении статуса источника.", show_alert=True)
        logger.error(f"Admin {callback.from_user.id} failed to toggle RSS source ID {source_id}.")