from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.inline import get_manager_panel, get_confirmation_keyboard, get_user_selection_keyboard
from utils.database import get_user_role, set_user_role, get_pending_news, approve_news, reject_news, remove_user_role, \
    get_users_by_role

router = Router()


# Состояния для назначения ролей
class AssignRole(StatesGroup):
    waiting_for_id = State()
    waiting_for_confirmation = State()


# Состояния для удаления ролей
class RemoveRole(StatesGroup):
    waiting_for_id = State()
    waiting_for_reason = State()
    waiting_for_confirmation = State()


# Состояния для проверки новостей
class ReviewNews(StatesGroup):
    waiting_for_action = State()


@router.callback_query(lambda c: c.data == "manager_panel")
async def manager_panel(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "manager":
        await callback.answer("🚫 Доступ запрещен!", show_alert=True)
        return
    await callback.message.edit_text(
        "📢 Панель менеджера\n"
        "Выберите действие 👇",
        reply_markup=get_manager_panel()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "assign_writer")
async def assign_writer(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "manager":
        await callback.answer("🚫 Доступ запрещен!", show_alert=True)
        return
    await callback.message.edit_text(
        "✍️ Введите ID пользователя, которого хотите назначить писателем:",
        reply_markup=None
    )
    await state.set_state(AssignRole.waiting_for_id)
    await state.update_data(role="writer")
    await callback.answer()


@router.message(AssignRole.waiting_for_id)
async def process_writer_id(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "manager":
        await message.answer("🚫 Доступ запрещен!")
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
            return

        await state.update_data(user_id=user_id)
        await message.answer(
            f"ℹ️ Пользователь с ID {user_id} имеет роль: {current_role}\n"
            f"Назначить роль {new_role}?",
            reply_markup=get_confirmation_keyboard("confirm_role", "cancel_role")
        )
        await state.set_state(AssignRole.waiting_for_confirmation)
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректный ID (целое число).",
            reply_markup=get_manager_panel()
        )
        await state.clear()


@router.callback_query(lambda c: c.data == "confirm_role")
async def confirm_role(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "manager":
        await callback.answer("🚫 Доступ запрещен!", show_alert=True)
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
        pass
    await state.clear()
    await callback.answer()


@router.callback_query(lambda c: c.data == "cancel_role")
async def cancel_role(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🚫 Назначение роли отменено.",
        reply_markup=get_manager_panel()
    )
    await state.clear()
    await callback.answer()


@router.callback_query(lambda c: c.data == "remove_writer")
async def remove_writer(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "manager":
        await callback.answer("🚫 Доступ запрещен!", show_alert=True)
        return
    writers = await get_users_by_role("writer")
    if not writers:
        await callback.message.edit_text(
            "📭 Нет писателей для удаления.",
            reply_markup=get_manager_panel()
        )
        await callback.answer()
        return
    print(f"Writers list: {writers}")  # Логирование для отладки
    await callback.message.edit_text(
        "✍️ Выберите писателя для удаления:",
        reply_markup=get_user_selection_keyboard(writers, "remove_writer")
    )
    await state.set_state(RemoveRole.waiting_for_id)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("select_user_"), RemoveRole.waiting_for_id)
async def process_remove_user_id(callback: CallbackQuery, state: FSMContext):
    print(f"Callback data: {callback.data}")  # Логирование для отладки
    parts = callback.data.split("_")
    if len(parts) < 5 or not parts[-1].isdigit():  # Проверяем, что последняя часть — число
        await callback.message.edit_text(
            "❌ Ошибка: некорректный выбор пользователя.",
            reply_markup=get_manager_panel()
        )
        await callback.answer()
        return
    user_id = int(parts[-1])  # Извлекаем user_id из последней части
    await state.update_data(user_id=user_id)
    await callback.message.edit_text(
        f"📝 Укажите причину удаления роли для пользователя с ID {user_id}:",
        reply_markup=None
    )
    await state.set_state(RemoveRole.waiting_for_reason)
    await callback.answer()


@router.message(RemoveRole.waiting_for_reason)
async def process_remove_reason(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "manager":
        await message.answer("🚫 Доступ запрещен!")
        return
    reason = message.text
    await state.update_data(reason=reason)
    data = await state.get_data()
    user_id = data["user_id"]
    await message.answer(
        f"ℹ️ Удалить роль пользователя с ID {user_id}?\nПричина: {reason}",
        reply_markup=get_confirmation_keyboard("confirm_remove_role", "cancel_remove_role")
    )
    await state.set_state(RemoveRole.waiting_for_confirmation)


@router.callback_query(lambda c: c.data == "confirm_remove_role")
async def confirm_remove_role(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "manager":
        await callback.answer("🚫 Доступ запрещен!", show_alert=True)
        return
    data = await state.get_data()
    user_id = data["user_id"]
    reason = data["reason"]
    role = await get_user_role(user_id)
    if role != "writer":
        await callback.message.edit_text(
            "🚫 Нельзя удалить эту роль!",
            reply_markup=get_manager_panel()
        )
        await state.clear()
        await callback.answer()
        return
    await remove_user_role(user_id)
    await callback.message.edit_text(
        f"✅ Роль пользователя с ID {user_id} удалена!",
        reply_markup=get_manager_panel()
    )
    try:
        await callback.message.bot.send_message(
            user_id,
            f"❌ Ваша роль {role} была удалена.\nПричина: {reason}"
        )
    except:
        pass
    await state.clear()
    await callback.answer()


@router.callback_query(lambda c: c.data == "cancel_remove_role")
async def cancel_remove_role(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🚫 Удаление роли отменено.",
        reply_markup=get_manager_panel()
    )
    await state.clear()
    await callback.answer()


@router.callback_query(lambda c: c.data == "review_news")
async def review_news(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "manager":
        await callback.answer("🚫 Доступ запрещен!", show_alert=True)
        return
    pending_news = await get_pending_news()
    if not pending_news:
        await callback.message.edit_text(
            "📭 Нет новостей на проверке.",
            reply_markup=get_manager_panel()
        )
        await callback.answer()
        return

    news = pending_news[0]
    response = (
        f"📰 Новость на проверке (ID: {news['pending_id']})\n"
        f"Категория: {news['category'].capitalize()}\n"
        f"Заголовок: {news['title']}\n"
        f"Описание: {news['description']}\n"
    )
    if news['image_url']:
        response += f"🖼 Картинка: {news['image_url']}\n"
    response += f"Автор ID: {news['author_id']}\n"

    await callback.message.edit_text(
        response,
        reply_markup=get_confirmation_keyboard(f"approve_news_{news['pending_id']}",
                                               f"reject_news_{news['pending_id']}")
    )
    await state.set_state(ReviewNews.waiting_for_action)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("approve_news_"))
async def approve_news_action(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "manager":
        await callback.answer("🚫 Доступ запрещен!", show_alert=True)
        return
    pending_id = int(callback.data.split("_")[2])
    author_id = await approve_news(pending_id)
    await callback.message.edit_text(
        "✅ Новость одобрена и опубликована!",
        reply_markup=get_manager_panel()
    )
    if author_id:
        try:
            await callback.message.bot.send_message(
                author_id,
                "🎉 Ваша новость была одобрена и опубликована!"
            )
        except:
            pass
    await state.clear()
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("reject_news_"))
async def reject_news_action(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "manager":
        await callback.answer("🚫 Доступ запрещен!", show_alert=True)
        return
    pending_id = int(callback.data.split("_")[2])
    author_id = await reject_news(pending_id)
    await callback.message.edit_text(
        "❌ Новость отклонена.",
        reply_markup=get_manager_panel()
    )
    if author_id:
        try:
            await callback.message.bot.send_message(
                author_id,
                "❌ Ваша новость была отклонена."
            )
        except:
            pass
    await state.clear()
    await callback.answer()