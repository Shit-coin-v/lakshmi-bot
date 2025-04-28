import logging

from aiogram import Bot
from aiogram.enums import ParseMode
from database.models import SessionLocal, CustomUser, engine
from aiogram.client.default import DefaultBotProperties


import config

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
logger = logging.getLogger(__name__)


async def send_broadcast_message(message_obj):
    async with bot:
        async with SessionLocal() as session:
            users = await session.execute(CustomUser.__table__.select())
            users = users.fetchall()

            for user in users:
                user_id = user.telegram_id
                try:
                    await bot.send_message(user_id, message_obj.message_text)
                    await engine.dispose()
                    logger.info(f"✅ Сообщение отправлено пользователю {user_id}")
                except Exception as e:
                    logger.warning(f"❌ Ошибка при отправке пользователю {user_id}: {e}")
