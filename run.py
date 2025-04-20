import os
import logging
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from dotenv import load_dotenv

import config
from database.models import SessionLocal
from database.models import create_db
from registration import UserRegistration
from keyboards import get_qr_code_button

load_dotenv()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


class Registration(StatesGroup):
    waiting_for_fio = State()
    waiting_for_birth_date = State()


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext):
    async with SessionLocal() as session:
        user_service = UserRegistration(session)
        user = await user_service.get_user_by_id(message.from_user.id)

        if user:
            text = f"Привет, {user.full_name}!"
            if user.qr_code and os.path.exists(user.qr_code):
                await message.answer(
                    text,
                    reply_markup=get_qr_code_button()
                )
            else:
                await message.answer(text)
        else:
            await state.update_data(
                telegram_id=message.from_user.id,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                full_name=message.from_user.full_name,
            )
            await message.answer("Добро пожаловать! Пожалуйста, введите ваше ФИО:")
            await state.set_state(Registration.waiting_for_fio)


@dp.callback_query(lambda c: c.data in ["show_qr", "show_bonuses"])
async def callback_handler(callback: CallbackQuery):
    async with SessionLocal() as session:
        user_service = UserRegistration(session)
        user = await user_service.get_user_by_id(callback.from_user.id)

        if not user:
            await callback.message.answer("Пользователь не найден")
            return await callback.answer()

        if callback.data == "show_qr":
            if not user.qr_code or not os.path.exists(user.qr_code):
                await callback.message.answer("QR-код не найден. Пожалуйста, обратитесь в поддержку")
                return await callback.answer()

            photo = FSInputFile(user.qr_code)
            await callback.message.answer_photo(photo)

        elif callback.data == "show_bonuses":
            await callback.message.answer(f"Ваши бонусы: {user.bonuses}")

    await callback.answer()


@dp.message(Registration.waiting_for_fio)
async def process_fio(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Введите вашу дату рождения (в формате ДД.ММ.ГГГГ):")
    await state.set_state(Registration.waiting_for_birth_date)


@dp.message(Registration.waiting_for_birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    try:
        birth_date = datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        await message.answer("Неверный формат. Введите дату как ДД.ММ.ГГГГ.")
        return

    data = await state.get_data()

    qr_code_path = None
    async with SessionLocal() as session:
        user_service = UserRegistration(session)
        user = await user_service.create_user(
            telegram_id=data["telegram_id"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            full_name=data["full_name"],
            birth_date=birth_date
        )
        qr_code_path = user.qr_code

    await message.answer("Спасибо! Вы успешно зарегистрированы.")

    if qr_code_path and os.path.exists(qr_code_path):
        await message.answer("Вот ваша кнопка для получения QR-кода:", reply_markup=get_qr_code_button())

    await state.clear()


async def main():
    await create_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
