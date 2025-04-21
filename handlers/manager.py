from mailbox import Message

from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.inline import get_manager_panel, get_confirmation_keyboard, get_user_selection_keyboard
from utils.database import get_user_role, set_user_role, get_pending_news, approve_news, reject_news, remove_user_role, \
    get_users_by_role, get_news_by_id, get_subscribers
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


@router.callback_query(lambda c: c.data == "manager_panel")
async def manager_panel(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "manager":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    await callback.message.edit_text(
        "📢 Панель менеджера\n"
        "Выберите действие 👇",
        reply_markup=get_manager_panel()
    )
    await callback.answer()
    logger.info(f"Manager {callback.from_user.id} opened manager panel.")


@router.callback_query(lambda c: c.data == "assign_writer")
async def assign_writer(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "manager":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    await callback.message.edit_text(
        "✍️ Введите ID пользователя, которого хотите назначить писателем:",
        reply_markup=None
    )
    await state.set_state(AssignRole.waiting_for_id)
    await state.update_data(role="writer")
    await callback.answer()
    logger.info(f"Manager {callback.from_user.id} started assigning writer role.")


@router.message(AssignRole.waiting_for_id)
async def process_role_id(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "manager":
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
                reply_markup=get_manager_panel()
            )
            await state.clear()
            logger.warning(
                f"Manager {message.from_user.id} tried to assign role {new_role} to user {user_id}, but user already has this role.")
            return

        await state.update_data(user_id=user_id)
        await message.answer(
            f"ℹ️ Пользователь с ID {user_id} имеет роль: {current_role}\n"
            f"Назначить роль {new_role}?",
            reply_markup=get_confirmation_keyboard("confirm_role", "cancel_role")
        )
        await state.set_state(AssignRole.waiting_for_confirmation)
        logger.info(f"Manager {message.from_user.id} selected user {user_id} to assign role {new_role}.")
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректный ID (целое число).",
            reply_markup=get_manager_panel()
        )
        await state.clear()
        logger.error(f"Manager {message.from_user.id} entered invalid user ID: {message.text}")


@router.callback_query(lambda c: c.data == "confirm_role")
async def confirm_role(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "manager":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    data = await state.get_data()
    user_id = data["user_id"]
    role = data["role"]
    await set_user_role(user_id, role)
    await callback.message.edit_text(
        f"✅ Пользователь с ID {user_id} назначен {role}!",
        reply_markup=get_manager_panel()
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
    logger.info(f"Manager {callback.from_user.id} assigned role {role} to user {user_id}.")


@router.callback_query(lambda c: c.data == "cancel_role")
async def cancel_role(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🚫 Назначение роли отменено.",
        reply_markup=get_manager_panel()
    )
    await state.clear()
    await callback.answer()
    logger.info(f"Manager {callback.from_user.id} canceled role assignment.")


@router.callback_query(lambda c: c.data == "remove_writer")
async def remove_writer(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "manager":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    writers = await get_users_by_role("writer")
    if not writers:
        await callback.message.edit_text(
            "📭 Нет писателей для удаления.",
            reply_markup=get_manager_panel()
        )
        await callback.answer()
        logger.info(f"Manager {callback.from_user.id} tried to remove writer, but no writers found.")
        return
    logger.info(f"Writers list for removal: {writers}")
    await callback.message.edit_text(
        "✍️ Выберите писателя для удаления:",
        reply_markup=get_user_selection_keyboard(writers, "remove_writer")
    )
    await state.set_state(RemoveRole.waiting_for_id)
    await callback.answer()
    logger.info(f"Manager {callback.from_user.id} started removing writer.")


@router.callback_query(lambda c: c.data.startswith("select_user_"), RemoveRole.waiting_for_id)
async def process_remove_user_id(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Callback data: {callback.data}")
    parts = callback.data.split("_")
    if len(parts) < 5 or not parts[-1].isdigit():
        await callback.message.edit_text(
            "❌ Ошибка: некорректный выбор пользователя.",
            reply_markup=get_manager_panel()
        )
        await callback.answer()
        logger.error(f"Manager {callback.from_user.id} provided invalid callback data: {callback.data}")
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
    logger.info(f"Manager {callback.from_user.id} selected user {user_id} for role removal.")


@router.message(RemoveRole.waiting_for_reason)
async def process_remove_reason(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "manager":
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
    logger.info(f"Manager {message.from_user.id} provided reason for role removal: {reason}")


@router.callback_query(lambda c: c.data == "confirm_remove_role")
async def confirm_remove_role(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "manager":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    data = await state.get_data()
    user_id = data["user_id"]
    reason = data["reason"]
    await remove_user_role(user_id)
    await callback.message.edit_text(
        f"✅ Роль пользователя с ID {user_id} удалена!\nПричина: {reason}",
        reply_markup=get_manager_panel()
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
    logger.info(f"Manager {callback.from_user.id} removed role from user {user_id} with reason: {reason}")


@router.callback_query(lambda c: c.data == "cancel_remove_role")
async def cancel_remove_role(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🚫 Удаление роли отменено.",
        reply_markup=get_manager_panel()
    )
    await state.clear()
    await callback.answer()
    logger.info(f"Manager {callback.from_user.id} canceled role removal.")


@router.callback_query(lambda c: c.data == "review_news")
async def review_news(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "manager":
        await callback.answer("🚫 Доступ запрещён!", show_alert=True)
        return
    pending_news = await get_pending_news()
    if not pending_news:
        await callback.message.edit_text(
            "📭 Нет новостей на проверку.",
            reply_markup=get_manager_panel()
        )
        await callback.answer()
        logger.info(f"Manager {callback.from_user.id} tried to review news, but no pending news found.")
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
    logger.info(f"Manager {callback.from_user.id} started reviewing news ID {news['pending_id']}.")


@router.callback_query(lambda c: c.data.startswith("approve_news_"))
async def approve_news_action(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "manager":
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
            reply_markup=get_manager_panel()
        )
        await state.clear()
    await callback.answer("✅ Новость одобрена!")
    logger.info(f"Manager {callback.from_user.id} approved news ID {pending_id}.")


@router.callback_query(lambda c: c.data.startswith("reject_news_"))
async def reject_news_action(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "manager":
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
            reply_markup=get_manager_panel()
        )
        await state.clear()
    await callback.answer("❌ Новость отклонена!")
    logger.info(f"Manager {callback.from_user.id} rejected news ID {pending_id}.")