import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from dotenv import load_dotenv

import config
from registration import UserRegistration
from onec_client import send_customer_to_onec
from keyboards import get_qr_code_button, get_consent_button
from database.models import SessionLocal, create_db, BotActivity, CustomUser
from qr_code import (
    resolve_qr_code_path,
    generate_qr_code,
    qr_code_filename,
)

load_dotenv()

logger = logging.getLogger(__name__)

bot: Bot | None = None
dp = Dispatcher()


def get_bot() -> Bot:
    if bot is None:
        raise RuntimeError("Telegram bot is not initialised")
    return bot


class Registration(StatesGroup):
    pass


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


async def ensure_qr_code_path(session, user: CustomUser):
    """Возвращает путь к файлу QR-кода, восстанавливая его при необходимости."""
    if not user or not user.qr_code:
        return None

    qr_code_value = str(user.qr_code).strip()
    path = None
    normalized_url = None

    try:
        path, normalized_url = resolve_qr_code_path(
            qr_code_value, telegram_id=user.telegram_id
        )
    except ValueError:
        logger.warning(
            "Не удалось преобразовать значение QR-кода в путь (telegram_id=%s, value=%r)",
            user.telegram_id,
            qr_code_value,
        )
    else:
        if path.exists():
            if normalized_url and normalized_url != qr_code_value:
                user.qr_code = normalized_url
                session.add(user)
                await session.commit()
            return path
        logger.warning(
            "Файл QR-кода не найден на диске (telegram_id=%s, path=%s)",
            user.telegram_id,
            path,
        )

    data_for_qr = qr_code_value if qr_code_value and path is None else str(user.telegram_id)
    filename = qr_code_filename(user.telegram_id)
    new_qr_value = generate_qr_code(
        data_for_qr, filename=filename, telegram_id=user.telegram_id
    )
    if user.qr_code != new_qr_value:
        user.qr_code = new_qr_value
        session.add(user)
        await session.commit()
    new_path, _ = resolve_qr_code_path(new_qr_value, telegram_id=user.telegram_id)
    return new_path


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext):
    async with SessionLocal() as session:
        user_service = UserRegistration(session)
        user = await user_service.get_user_by_id(message.from_user.id)


        if user:
            text = "Привет!"
            qr_path = await ensure_qr_code_path(session, user)
            if qr_path and qr_path.exists():
                await message.answer(text, reply_markup=get_qr_code_button())
                return
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
                    "Прежде чем начать, пожалуйста, ознакомьтесь с условиями обработки персональных данных.\n\n"
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
        data = await state.get_data()
        user = await user_service.create_user(
            telegram_id=callback.from_user.id,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
            referrer_id=data.get("referrer_id"),
            personal_data_consent=True,
        )

        await send_customer_to_onec(session, user, data.get("referrer_id"))

    await callback.message.answer("Спасибо! Вы успешно зарегистрированы.")
    if user.qr_code:
        qr_path, _ = resolve_qr_code_path(
            user.qr_code, telegram_id=user.telegram_id
        )
        if qr_path.exists():
            await callback.message.answer(
                "Вот ваша кнопка для получения QR-кода:",
                reply_markup=get_qr_code_button(),
            )
    await state.clear()
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
            qr_path = await ensure_qr_code_path(session, user)
            if not qr_path or not qr_path.exists():
                await callback.message.answer("QR-код не найден. Пожалуйста, обратитесь в поддержку")
                return await callback.answer()

            photo = FSInputFile(str(qr_path))
            await callback.message.answer_photo(photo)

        elif callback.data == "show_bonuses":
            await callback.message.answer(f"Ваши бонусы: {user.bonuses}")

        elif callback.data == "invite_friend":
            bot_info = await get_bot().get_me()
            bot_username = bot_info.username
            ref_link = f"https://t.me/{bot_username}?start=ref{user.telegram_id}"
            await callback.message.answer(f"🔗 Ваша реферальная ссылка:\n{ref_link}")

    await callback.answer()




async def main():
    global bot
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await create_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not configured; Telegram bot will not start")
        raise SystemExit(1)
    asyncio.run(main())

