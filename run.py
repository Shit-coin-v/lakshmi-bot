import logging
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from dotenv import load_dotenv

import config
from database.models import SessionLocal
from database.models import create_db
from registration import UserRegistration

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
            await message.answer(f"Привет, {user.full_name}!")
        else:
            await state.update_data(
                telegram_id=message.from_user.id,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                full_name=message.from_user.full_name,
            )
            await message.answer("Добро пожаловать! Пожалуйста, введите ваше ФИО:")
            await state.set_state(Registration.waiting_for_fio)


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
    async with SessionLocal() as session:
        user_service = UserRegistration(session)
        await user_service.create_user(
            telegram_id=data["telegram_id"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            full_name=data["full_name"],
            birth_date=birth_date
        )

    await message.answer("Спасибо! Вы успешно зарегистрированы.")
    await state.clear()


async def main():
    await create_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
