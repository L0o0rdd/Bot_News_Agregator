from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config.config import ADMIN_ID, ROLES
from keyboards.inline import get_admin_panel

router = Router()

# Состояния для назначения менеджера
class AssignManager(StatesGroup):
    waiting_for_id = State()

@router.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("🚫 Доступ запрещен!", show_alert=True)
        return
    await callback.message.edit_text(
        "🛠 Админ-панель\n"
        "Выберите действие 👇",
        reply_markup=get_admin_panel()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "assign_manager")
async def assign_manager(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("🚫 Доступ запрещен!", show_alert=True)
        return
    await callback.message.edit_text(
        "👤 Введите ID пользователя, которого хотите назначить менеджером:",
        reply_markup=None
    )
    await state.set_state(AssignManager.waiting_for_id)
    await callback.answer()

@router.message(AssignManager.waiting_for_id)
async def process_manager_id(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("🚫 Доступ запрещен!")
        return
    try:
        user_id = int(message.text)
        if user_id in ROLES["admin"]:
            await message.answer(
                "🚫 Этот пользователь уже администратор!",
                reply_markup=get_admin_panel()
            )
        elif user_id in ROLES["manager"]:
            await message.answer(
                "🚫 Этот пользователь уже менеджер!",
                reply_markup=get_admin_panel()
            )
        else:
            ROLES["manager"].append(user_id)
            await message.answer(
                f"✅ Пользователь с ID {user_id} назначен менеджером!",
                reply_markup=get_admin_panel()
            )
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректный ID (целое число).",
            reply_markup=get_admin_panel()
        )
    await state.clear()