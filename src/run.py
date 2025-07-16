import os
import re
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
from sqlalchemy import select

from dotenv import load_dotenv

import config
from registration import UserRegistration
from keyboards import get_qr_code_button, get_consent_button
from database.models import SessionLocal, create_db, BotActivity, CustomUser

load_dotenv()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


class Registration(StatesGroup):
    waiting_for_fio = State()
    waiting_for_birth_date = State()


async def save_bot_activity(session, telegram_id: int, action: str):
    """Сохраняет активность пользователя"""
    user = await session.execute(
        select(CustomUser).where(CustomUser.telegram_id == telegram_id)
    )
    user = user.scalar_one_or_none()

    if user:
        activity = BotActivity(
            customer_id=user.id,
            action=action,
            timestamp=datetime.utcnow()
        )
        session.add(activity)
        await session.commit()


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext):
    async with SessionLocal() as session:
        user_service = UserRegistration(session)
        user = await user_service.get_user_by_id(message.from_user.id)

        await save_bot_activity(session, telegram_id=message.from_user.id, action="start")

        if user:
            text = f"Привет, {user.full_name}!"
            if user.qr_code and os.path.exists(user.qr_code):
                await message.answer(text, reply_markup=get_qr_code_button())
            else:
                await message.answer(text)
        else:
            command_args = message.text.split()
            referrer_id = None
            if len(command_args) > 1 and command_args[1].startswith('ref'):
                try:
                    referrer_id = int(command_args[1][3:])
                    if not await user_service.get_user_by_id(referrer_id):
                        referrer_id = None
                except ValueError:
                    referrer_id = None

            await state.update_data(
                telegram_id=message.from_user.id,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                referrer_id=referrer_id
            )

            await message.answer(
                text=(
                    "👋 Здравствуйте!\n"
                    "Добро пожаловать в нашу систему лояльности.\n"
                    "Прежде чем начать регистрацию, пожалуйста, ознакомьтесь с "
                    "условиями обработки персональных данных.\n"
                    "🔐 Мы собираем и обрабатываем следующие данные:\n"
                    " • ФИО\n"
                    " • Дата рождения\n"
                    " • Telegram ID\n"
                    "\n"
                    "Цель обработки данных:\n"
                    " • Регистрация в бонусной программе\n"
                    " • Персонализированные предложения\n"
                    " • Ведение внутренней аналитики\n\n"
                    "📄 Полный текст политики доступен здесь:\n"
                    "👉 https://docs.google.com/document/d/13BI-g30MvueQS2fSvaVdnKA9M2LkyEBUTaJ0GFI5f2g/edit?usp=sharing\n\n"
                    "Нажимая кнопку «Я согласен», вы подтверждаете своё согласие на обработку персональных данных "
                    "в соответствии с Федеральным законом №152-ФЗ.\n\n"
                    "⬇️ Пожалуйста, нажмите кнопку «Я согласен», чтобы продолжить."
                ),
                reply_markup=get_consent_button()
            )


@dp.callback_query(lambda c: c.data == "personal_data_agree")
async def consent_callback(callback: CallbackQuery, state: FSMContext):
    async with SessionLocal() as session:
        user_service = UserRegistration(session)
        existing_user = await user_service.get_user_by_id(callback.from_user.id)
        if existing_user:
            await callback.message.answer("Вы уже зарегистрированы.")
            return await callback.answer()

        await state.update_data(personal_data_consent=True)
        await callback.message.answer("Спасибо за согласие. Пожалуйста, введите ваше ФИО:")
        await state.set_state(Registration.waiting_for_fio)

    await callback.answer()


@dp.callback_query(lambda c: c.data in ["show_qr", "show_bonuses", "invite_friend"])
async def callback_handler(callback: CallbackQuery):
    async with SessionLocal() as session:
        user_service = UserRegistration(session)
        user = await user_service.get_user_by_id(callback.from_user.id)

        if not user:
            await callback.message.answer("Пользователь не найден")
            return await callback.answer()

        await save_bot_activity(session, telegram_id=callback.from_user.id, action=callback.data)

        if callback.data == "show_qr":
            if not user.qr_code or not os.path.exists(user.qr_code):
                await callback.message.answer("QR-код не найден. Пожалуйста, обратитесь в поддержку")
                return await callback.answer()

            photo = FSInputFile(user.qr_code)
            await callback.message.answer_photo(photo)

        elif callback.data == "show_bonuses":
            await callback.message.answer(f"Ваши бонусы: {user.bonuses}")

        elif callback.data == "invite_friend":
            bot_info = await bot.get_me()
            bot_username = bot_info.username
            ref_link = f"https://t.me/{bot_username}?start=ref{user.telegram_id}"
            await callback.message.answer(f"🔗 Ваша реферальная ссылка:\n{ref_link}")

    await callback.answer()


@dp.message(Registration.waiting_for_fio)
async def process_fio(message: Message, state: FSMContext):
    FIO_REGEX = r"^[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+$"
    if not re.match(FIO_REGEX, message.text.strip()):
        await message.answer(
            "❌ Некорректный формат ФИО.\n"
            "Например: <b>Иванов Иван Иванович</b>",
            parse_mode="HTML"
        )
        return

    await state.update_data(full_name=message.text.strip())
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
        user = await user_service.create_user(
            telegram_id=data["telegram_id"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            full_name=data["full_name"],
            birth_date=birth_date,
            referrer_id=data.get("referrer_id"),
            personal_data_consent=data.get("personal_data_consent", False)
        )

    await message.answer("Спасибо! Вы успешно зарегистрированы.")
    if user.qr_code and os.path.exists(user.qr_code):
        await message.answer("Вот ваша кнопка для получения QR-кода:", reply_markup=get_qr_code_button())

    await state.clear()


async def main():
    await create_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
