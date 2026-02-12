from __future__ import annotations

import logging
from datetime import date

import requests
from celery import shared_task
from apps.loyalty.models import CustomUser

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
)
def send_order_push_task(self, order_id: int, previous_status: str):
    """Send FCM push for order status change (non-blocking via Celery)."""
    from apps.orders.models import Order
    from apps.notifications.push import notify_order_status_change

    order = Order.objects.select_related("customer").get(id=order_id)
    notify_order_status_change(order, previous_status=previous_status)


@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
)
def send_push_notification_task(self, notification_id: int):
    """Send FCM push for a newly created notification (non-blocking via Celery)."""
    from django.core.exceptions import ImproperlyConfigured
    from apps.notifications.models import Notification
    from apps.notifications.push import notify_notification_created

    notification = Notification.objects.select_related("user").get(id=notification_id)
    try:
        result = notify_notification_created(notification)
    except ImproperlyConfigured:
        logger.warning("Firebase not configured; skipping push for notification id=%s", notification_id)
        return
    logger.info(
        "Push sent for notification id=%s result=%s",
        notification_id,
        {k: result.get(k) for k in ("sent", "success", "failure")},
    )


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



@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def notify_couriers_new_order(self, order_id: int):
    """Send new order notification to all couriers."""
    from django.conf import settings as django_settings
    from apps.orders.models import Order

    bot_token = getattr(django_settings, "COURIER_BOT_TOKEN", "")
    courier_ids = getattr(django_settings, "COURIER_ALLOWED_TG_IDS", [])
    if not bot_token or not courier_ids:
        logger.warning("COURIER_BOT_TOKEN or COURIER_ALLOWED_TG_IDS not configured; skipping courier notification")
        return

    order = Order.objects.filter(id=order_id).only("id", "total_price", "address").first()
    if not order:
        return

    total = int(order.total_price) if order.total_price == int(order.total_price) else float(order.total_price)
    text = f"\U0001f514 <b>\u041d\u043e\u0432\u044b\u0439 \u0437\u0430\u043a\u0430\u0437 #{order_id}!</b>\n\U0001f4b0 {total}\u20bd"
    if order.address:
        text += f"\n\U0001f3e0 {order.address}"
    text += "\n\nНажмите /orders для подробностей."

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    from apps.notifications.models import CourierNotificationMessage

    sent, errors = 0, 0
    for courier_id in courier_ids:
        try:
            resp = requests.post(url, json={
                "chat_id": courier_id,
                "text": text,
                "parse_mode": "HTML",
            }, timeout=5)
            resp.raise_for_status()
            msg_data = resp.json()
            if msg_data.get("ok"):
                CourierNotificationMessage.objects.create(
                    courier_tg_id=courier_id,
                    telegram_message_id=msg_data["result"]["message_id"],
                )
            sent += 1
        except requests.RequestException as e:
            logger.error("Courier notification failed for %s: %s", courier_id, e)
            errors += 1

    logger.info("Courier notification for order #%s: sent=%d, errors=%d", order_id, sent, errors)
