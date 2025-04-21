from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from keyboards.inline import get_main_menu
from utils.database import get_user_role, set_user_role

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    role = await get_user_role(user_id)

    if role == "user":
        await set_user_role(user_id, "user")

    if role == "admin":
        await message.answer(
            "👑 Добро пожаловать, Админ!\n"
            "Вы можете управлять ботом и настраивать новости.\n"
            "Выберите действие в меню ниже 👇",
            reply_markup=get_main_menu("admin")
        )
    elif role == "manager":
        await message.answer(
            "🧑‍💼 Привет, Менеджер!\n"
            "Вы можете публиковать и проверять новости.\n"
            "Выберите действие в меню ниже 👇",
            reply_markup=get_main_menu("manager")
        )
    elif role == "writer":
        await message.answer(
            "✍️ Привет, Писатель!\n"
            "Вы можете создавать свои новости.\n"
            "Выберите действие в меню ниже 👇",
            reply_markup=get_main_menu("writer")
        )
    else:
        await message.answer(
            "👋 Привет, Юзер!\n"
            "Я бот для новостей! Читайте свежие новости и наслаждайтесь.\n"
            "Выберите действие в меню ниже 👇",
            reply_markup=get_main_menu("user")
        )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    role = await get_user_role(callback.from_user.id)
    await callback.message.edit_text(
        f"🔙 Вернулись в главное меню!\nВыберите действие 👇",
        reply_markup=get_main_menu(role)
    )
    await callback.answer()