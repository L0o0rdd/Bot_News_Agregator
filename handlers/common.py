from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from keyboards.inline import get_main_menu
from config.config import ROLES, ADMIN_ID

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    if user_id in ROLES["admin"]:
        await message.answer(
            "👑 Добро пожаловать, Админ!\n"
            "Вы можете управлять ботом и настраивать новости.\n"
            "Выберите действие в меню ниже 👇",
            reply_markup=get_main_menu("admin")
        )
    elif user_id in ROLES["manager"]:
        await message.answer(
            "🧑‍💼 Привет, Менеджер!\n"
            "Вы можете публиковать новости.\n"
            "Выберите действие в меню ниже 👇",
            reply_markup=get_main_menu("manager")
        )
    else:
        ROLES["user"].append(user_id)
        await message.answer(
            "👋 Привет, Юзер!\n"
            "Я бот для новостей! Читайте свежие новости и наслаждайтесь.\n"
            "Выберите действие в меню ниже 👇",
            reply_markup=get_main_menu("user")
        )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    role = "user"
    if user_id in ROLES["admin"]:
        role = "admin"
    elif user_id in ROLES["manager"]:
        role = "manager"

    await callback.message.edit_text(
        f"🔙 Вернулись в главное меню!\nВыберите действие 👇",
        reply_markup=get_main_menu(role)
    )
    await callback.answer()