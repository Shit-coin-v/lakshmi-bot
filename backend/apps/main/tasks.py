# backend/apps/main/tasks.py
import asyncio
import logging
from celery import shared_task
from django.db import close_old_connections

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def broadcast_send_task(self, message_id: int) -> None:
    """Фоновая отправка рассылки через Django ORM (без SQLAlchemy)."""
    close_old_connections()

    # ленивые импорты, чтобы избежать циклов и привязать всё к текущему loop
    from aiogram import Bot
    from aiogram.enums import ParseMode
    from aiogram.client.default import DefaultBotProperties

    from bots.customer_bot.broadcast import _send_with_django, BOT_TOKEN

    async def runner():
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        try:
            await _send_with_django(message_id, bot_instance=bot)
        finally:
            await bot.session.close()

    asyncio.run(runner())
