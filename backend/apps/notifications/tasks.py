from __future__ import annotations

import logging
from datetime import date

import requests
from celery import shared_task
from apps.loyalty.models import CustomUser

logger = logging.getLogger(__name__)

# Best-effort dedup TTL (сек) для push-задач, привязанных к событиям.
# Защищает от re-delivery Celery (секунды-минуты), но не блокирует
# легитимные повторные переходы статуса. Не exactly-once (нужен DB/outbox).
_DEDUP_SENT_TTL = 7200  # 2 часа


@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
)
def send_order_push_task(self, order_id: int, previous_status: str, new_status: str):
    """Send FCM push for order status change (non-blocking via Celery)."""
    from django.core.cache import cache
    from apps.orders.models import Order
    from apps.notifications.push import notify_order_status_change

    cache_key = f"push:order:{order_id}:{previous_status}->{new_status}"
    if not cache.add(cache_key, "processing", timeout=300):
        logger.info("Push already processed/in-progress for order %s (%s->%s)", order_id, previous_status, new_status)
        return

    try:
        order = Order.objects.select_related("customer").get(id=order_id)
        notify_order_status_change(order, previous_status=previous_status, new_status=new_status)
        cache.set(cache_key, "sent", timeout=_DEDUP_SENT_TTL)
    except Exception:
        cache.delete(cache_key)
        raise


@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
)
def send_push_notification_task(self, notification_id: int):
    """Send FCM push for a newly created notification (non-blocking via Celery)."""
    from django.core.cache import cache
    from django.core.exceptions import ImproperlyConfigured
    from apps.notifications.models import Notification
    from apps.notifications.push import notify_notification_created

    cache_key = f"push:notif:{notification_id}"
    if not cache.add(cache_key, "processing", timeout=300):
        logger.info("Push already processed/in-progress for notification %s", notification_id)
        return

    try:
        notification = Notification.objects.select_related("user").get(id=notification_id)
        try:
            result = notify_notification_created(notification)
        except ImproperlyConfigured:
            logger.warning("Firebase not configured; skipping push for notification id=%s", notification_id)
            cache.set(cache_key, "no_firebase", timeout=86400)
            return
        cache.set(cache_key, "sent", timeout=86400)
        logger.info(
            "Push sent for notification id=%s result=%s",
            notification_id,
            {k: result.get(k) for k in ("sent", "success", "failure")},
        )
    except Exception:
        cache.delete(cache_key)
        raise


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
def notify_pickers_new_order(self, order_id: int):
    """Send new order notification to all pickers."""
    from django.core.cache import cache
    from django.conf import settings as django_settings
    from apps.orders.models import Order

    cache_key = f"push:pickers:{order_id}"
    if not cache.add(cache_key, "processing", timeout=300):
        logger.info("Picker notification already processed/in-progress for order %s", order_id)
        return

    try:
        bot_token = getattr(django_settings, "PICKER_BOT_TOKEN", "")
        picker_ids = getattr(django_settings, "PICKER_ALLOWED_TG_IDS", [])
        if not bot_token or not picker_ids:
            logger.warning("PICKER_BOT_TOKEN or PICKER_ALLOWED_TG_IDS not configured; skipping picker notification")
            cache.set(cache_key, "no_config", timeout=86400)
            return

        order = Order.objects.filter(id=order_id).only("id", "total_price", "address", "fulfillment_type").first()
        if not order:
            cache.set(cache_key, "no_order", timeout=86400)
            return

        total = int(order.total_price) if order.total_price == int(order.total_price) else float(order.total_price)
        fulfillment = "🚚 Доставка" if order.fulfillment_type == "delivery" else "🏪 Самовывоз"
        text = f"🔔 <b>Новый заказ #{order_id}!</b>\n💰 {total}₽\n{fulfillment}"
        if order.address:
            text += f"\n🏠 {order.address}"
        text += "\n\nНажмите /orders для подробностей."

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        from apps.notifications.models import PickerNotificationMessage

        sent, errors = 0, 0
        for picker_id in picker_ids:
            try:
                resp = requests.post(url, json={
                    "chat_id": picker_id,
                    "text": text,
                    "parse_mode": "HTML",
                }, timeout=5)
                resp.raise_for_status()
                msg_data = resp.json()
                if msg_data.get("ok"):
                    PickerNotificationMessage.objects.create(
                        picker_tg_id=picker_id,
                        telegram_message_id=msg_data["result"]["message_id"],
                    )
                sent += 1
            except requests.RequestException as e:
                logger.error("Picker notification failed for %s: %s", picker_id, e)
                errors += 1

        logger.info("Picker notification for order #%s: sent=%d, errors=%d", order_id, sent, errors)
        if errors > 0 and self.request.retries < self.max_retries:
            cache.delete(cache_key)
            raise self.retry(
                exc=RuntimeError(f"Partial delivery: sent={sent}, errors={errors}"),
                countdown=10 + self.request.retries * 5,
            )
        cache.set(cache_key, "sent", timeout=_DEDUP_SENT_TTL)
    except Exception:
        cache.delete(cache_key)
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def notify_couriers_new_order(self, order_id: int):
    """Send new order notification to all couriers."""
    from django.core.cache import cache
    from django.conf import settings as django_settings
    from apps.orders.models import Order

    cache_key = f"push:couriers:{order_id}"
    if not cache.add(cache_key, "processing", timeout=300):
        logger.info("Courier notification already processed/in-progress for order %s", order_id)
        return

    try:
        bot_token = getattr(django_settings, "COURIER_BOT_TOKEN", "")
        courier_ids = getattr(django_settings, "COURIER_ALLOWED_TG_IDS", [])
        if not bot_token or not courier_ids:
            logger.warning("COURIER_BOT_TOKEN or COURIER_ALLOWED_TG_IDS not configured; skipping courier notification")
            cache.set(cache_key, "no_config", timeout=86400)
            return

        order = Order.objects.filter(id=order_id).only("id", "total_price", "address").first()
        if not order:
            cache.set(cache_key, "no_order", timeout=86400)
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
        if errors > 0 and self.request.retries < self.max_retries:
            cache.delete(cache_key)  # разрешить retry
            raise self.retry(
                exc=RuntimeError(f"Partial delivery: sent={sent}, errors={errors}"),
                countdown=10 + self.request.retries * 5,
            )
        cache.set(cache_key, "sent", timeout=_DEDUP_SENT_TTL)
    except Exception:
        cache.delete(cache_key)
        raise
