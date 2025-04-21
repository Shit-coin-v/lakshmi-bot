import logging

from aiogram import Bot
from aiogram.enums import ParseMode
from database.models import SessionLocal, CustomUser
from aiogram.client.default import DefaultBotProperties


import config

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
logger = logging.getLogger(__name__)


async def send_broadcast_message(message_obj):
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    async with bot:
        async with SessionLocal() as session:
            if message_obj.send_to_all:
                users = (await session.execute(
                    CustomUser.__table__.select()
                )).fetchall()

                for user in users:
                    user_id = user.telegram_id
                    try:
                        await bot.send_message(user_id, message_obj.message_text)
                        logger.info(f"✅ Сообщение отправлено пользователю {user_id}")
                    except Exception as e:
                        logger.warning(f"❌ Ошибка при отправке пользователю {user_id}: {e}")
            else:
                user_id = message_obj.target_user_id
                try:
                    await bot.send_message(user_id, message_obj.message_text)
                    logger.info(f"✅ Сообщение отправлено пользователю {user_id}")
                except Exception as e:
                    logger.warning(f"❌ Ошибка при отправке пользователю {user_id}: {e}")
