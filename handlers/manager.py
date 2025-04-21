from aiogram import Router
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(lambda c: c.data == "manager_panel")
async def manager_panel(callback: CallbackQuery):
    await callback.message.edit_text(
        "📢 Панель менеджера\n"
        "Здесь вы можете публиковать новости.\n"
        "Выберите действие 👇",
        reply_markup=None  # TODO: Добавить клавиатуру менеджера
    )
    await callback.answer()