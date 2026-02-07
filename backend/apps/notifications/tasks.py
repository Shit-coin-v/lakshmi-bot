from __future__ import annotations

import logging
from datetime import date

import requests
from celery import shared_task
from apps.loyalty.models import CustomUser

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def send_birthday_congratulations(self):
    from django.conf import settings as django_settings

    today = date.today()
    bot_token = getattr(django_settings, "TELEGRAM_BOT_TOKEN", "") or ""
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not configured; skipping birthdays")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    birthday_users = (
        CustomUser.objects
        .filter(birth_date__month=today.month, birth_date__day=today.day)
        .exclude(telegram_id__isnull=True)
        .only("telegram_id", "full_name")
        .iterator(chunk_size=100)
    )

    sent, errors = 0, 0
    for user in birthday_users:
        message = (
            f"\U0001f389 Поздравляем тебя с Днём Рождения, {user.full_name or 'друг'}! "
            f"Желаем счастья, здоровья и успехов! \U0001f382"
        )
        try:
            resp = requests.post(
                url, json={"chat_id": user.telegram_id, "text": message}, timeout=5,
            )
            resp.raise_for_status()
            sent += 1
        except requests.RequestException as e:
            logger.error("Birthday msg failed for %s: %s", user.telegram_id, e)
            errors += 1

    logger.info("Birthday congratulations: sent=%d, errors=%d", sent, errors)
