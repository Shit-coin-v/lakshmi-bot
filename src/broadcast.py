import os
import logging
import secrets

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from dotenv import load_dotenv

from src.database.models import (
    SessionLocal,
    CustomUser,
    NewsletterDelivery,
    engine,
)

load_dotenv()

logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN не задан в переменных окружения. Рассылка остановлена.")
    raise RuntimeError("BOT_TOKEN is required for broadcast")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


OPEN_CALLBACK_PREFIX = "open:"


async def _token_exists(session, token: str) -> bool:
    result = await session.execute(
        select(NewsletterDelivery.id).where(NewsletterDelivery.open_token == token)
    )
    return result.scalar_one_or_none() is not None


async def generate_unique_open_token(session, *, max_attempts: int = 10) -> str:
    for attempt in range(max_attempts):
        token = secrets.token_hex(16)
        if not await _token_exists(session, token):
            return token
        logger.debug("Collision on newsletter open token %s (attempt %s)", token, attempt + 1)
    raise RuntimeError("Unable to generate unique open token")


async def send_broadcast_message(message_obj):
    async with bot:
        async with SessionLocal() as session:
            if message_obj.send_to_all:
                users = await session.execute(
                    select(CustomUser).where(CustomUser.telegram_id > 0)
                )
                users = users.scalars().all()
            else:
                target_ids = message_obj.target_user_ids
                if not target_ids:
                    logger.warning("❌ Не указаны целевые пользователи")
                    return

                try:
                    user_ids = [int(id.strip()) for id in target_ids.split(',')]
                except ValueError as e:
                    logger.error(f"❌ Ошибка парсинга ID: {e}")
                    return

                users = await session.execute(
                    select(CustomUser)
                    .where(CustomUser.telegram_id.in_(user_ids))
                    .where(CustomUser.telegram_id > 0)
                )
                users = users.scalars().all()

            success, errors = 0, 0
            for user in users:
                try:
                    token = await generate_unique_open_token(session)
                    keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text="Показать",
                                    callback_data=f"{OPEN_CALLBACK_PREFIX}{token}",
                                )
                            ]
                        ]
                    )
                    spoiler_text = f"<tg-spoiler>{message_obj.message_text}</tg-spoiler>"
                    sent_message = await bot.send_message(
                        user.telegram_id,
                        spoiler_text,
                        reply_markup=keyboard,
                    )
                    delivery = NewsletterDelivery(
                        message_id=message_obj.id,
                        customer_id=user.id,
                        chat_id=sent_message.chat.id,
                        telegram_message_id=sent_message.message_id,
                        open_token=token,
                    )
                    session.add(delivery)
                    await session.commit()
                    success += 1
                    logger.info("✅ Отправлено %s (token=%s)", user.telegram_id, token)
                except Exception as e:
                    await session.rollback()
                    errors += 1
                    logger.error(f"❌ Ошибка {user.telegram_id}: {str(e)}")

            logger.info(f"Итог: Успешно — {success}, Ошибок — {errors}")
            await engine.dispose()
