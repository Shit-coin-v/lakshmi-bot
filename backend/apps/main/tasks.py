# backend/apps/main/tasks.py
import logging

import requests
from asgiref.sync import async_to_sync
from celery import shared_task
from django.conf import settings
from django.db import close_old_connections

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_telegram_message_task(self, telegram_id: int, text: str):
    """Отправка сообщения в Telegram через Celery (C11)."""
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not configured")
        return {"status": "error", "reason": "no_token"}

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": telegram_id, "text": text, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
        return {"status": "sent"}
    except requests.RequestException as exc:
        logger.warning("Failed to send Telegram message: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=300)
def broadcast_send_task(self, message_id: int) -> None:
    """Фоновая отправка рассылки через Django ORM (без SQLAlchemy)."""
    close_old_connections()

    # ленивые импорты, чтобы избежать циклов и привязать всё к текущему loop
    from aiogram import Bot
    from aiogram.enums import ParseMode
    from aiogram.client.default import DefaultBotProperties
    from shared.broadcast import send_with_django

    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""

    async def runner():
        bot = None
        if bot_token and ":" in bot_token:
            bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        try:
            await send_with_django(message_id, bot_instance=bot)
        finally:
            if bot:
                await bot.session.close()

    async_to_sync(runner)()
