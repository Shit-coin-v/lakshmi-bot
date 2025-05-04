import os
import logging

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from sqlalchemy import select
from dotenv import load_dotenv

from src.database.models import SessionLocal, CustomUser, engine

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token='7021373751:AAFzYF2sM8BNTUTbLv7hbTGNBO23PHmqIUg', default=DefaultBotProperties(parse_mode=ParseMode.HTML))
logger = logging.getLogger(__name__)


async def send_broadcast_message(message_obj):
    async with bot:
        async with SessionLocal() as session:
            if message_obj.send_to_all:
                users = await session.execute(select(CustomUser))
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
                    select(CustomUser).where(CustomUser.telegram_id.in_(user_ids)))
                users = users.scalars().all()

            success, errors = 0, 0
            for user in users:
                try:
                    await bot.send_message(user.telegram_id, message_obj.message_text)
                    success += 1
                    logger.info(f"✅ Отправлено {user.telegram_id}")
                except Exception as e:
                    errors += 1
                    logger.error(f"❌ Ошибка {user.telegram_id}: {str(e)}")

            logger.info(f"Итог: Успешно — {success}, Ошибок — {errors}")
            await engine.dispose()
