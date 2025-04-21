from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.inline import get_category_keyboard, get_writer_panel
from config.config import CATEGORIES, BOT_TOKEN
from utils.database import get_user_role, submit_news

router = Router()


# Состояния для создания новости
class CreateNews(StatesGroup):
    waiting_for_category = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_image = State()


@router.callback_query(lambda c: c.data == "writer_panel")
async def writer_panel(callback: CallbackQuery):
    if await get_user_role(callback.from_user.id) != "writer":
        await callback.answer("🚫 Доступ запрещен!", show_alert=True)
        return
    await callback.message.edit_text(
        "✍️ Панель писателя\n"
        "Выберите действие 👇",
        reply_markup=get_writer_panel()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "create_news")
async def create_news(callback: CallbackQuery, state: FSMContext):
    if await get_user_role(callback.from_user.id) != "writer":
        await callback.answer("🚫 Доступ запрещен!", show_alert=True)
        return
    await callback.message.edit_text(
        "📰 Выберите категорию для новости:",
        reply_markup=get_category_keyboard()
    )
    await state.set_state(CreateNews.waiting_for_category)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("category_"), CreateNews.waiting_for_category)
async def process_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("_")[1]
    await state.update_data(category=category)
    await callback.message.edit_text(
        "📝 Введите заголовок новости:",
        reply_markup=None
    )
    await state.set_state(CreateNews.waiting_for_title)
    await callback.answer()


@router.message(CreateNews.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "writer":
        await message.answer("🚫 Доступ запрещен!")
        return
    await state.update_data(title=message.text)
    await message.answer(
        "📜 Введите текст новости:",
        reply_markup=None
    )
    await state.set_state(CreateNews.waiting_for_description)


@router.message(CreateNews.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "writer":
        await message.answer("🚫 Доступ запрещен!")
        return
    await state.update_data(description=message.text)
    await message.answer(
        "🖼 Прикрепите картинку (или отправьте 'Пропустить' для отправки без картинки):",
        reply_markup=None
    )
    await state.set_state(CreateNews.waiting_for_image)


@router.message(CreateNews.waiting_for_image)
async def process_image(message: Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "writer":
        await message.answer("🚫 Доступ запрещен!")
        return
    data = await state.get_data()

    image_url = None
    if message.text and message.text.lower() != "пропустить":
        await message.answer(
            "❌ Пожалуйста, прикрепите картинку или отправьте 'Пропустить'.",
            reply_markup=get_writer_panel()
        )
        return
    elif message.photo:
        # Получаем последнюю (самую большую) версию фото
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        image_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    await submit_news(
        category=data["category"],
        title=data["title"],
        description=data["description"],
        author_id=message.from_user.id,
        image_url=image_url
    )
    await message.answer(
        "✅ Новость отправлена на проверку!",
        reply_markup=get_writer_panel()
    )
    await state.clear()