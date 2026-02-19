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
        from apps.orders.models import PickerProfile
        bot_token = getattr(django_settings, "PICKER_BOT_TOKEN", "")
        picker_ids = list(
            PickerProfile.objects.filter(is_approved=True, is_blacklisted=False)
            .values_list("telegram_id", flat=True)
        )
        if not bot_token or not picker_ids:
            logger.warning("PICKER_BOT_TOKEN or no approved pickers; skipping picker notification")
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

        sent, skipped, errors = 0, 0, 0
        for picker_id in picker_ids:
            # Skip pickers already notified (on retry after partial failure)
            per_picker_key = f"push:picker:{order_id}:{picker_id}"
            if cache.get(per_picker_key):
                skipped += 1
                continue
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
                cache.set(per_picker_key, 1, timeout=_DEDUP_SENT_TTL)
                sent += 1
            except requests.RequestException as e:
                logger.error("Picker notification failed for %s: %s", picker_id, e)
                errors += 1

        logger.info("Picker notification for order #%s: sent=%d, skipped=%d, errors=%d", order_id, sent, skipped, errors)
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
    """DEPRECATED — kept for backward compat. Use assign_courier_task instead."""
    logger.warning("notify_couriers_new_order called for order %s — this is deprecated, use assign_courier_task", order_id)
    assign_courier_task.delay(order_id)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def assign_courier_task(self, order_id: int):
    """Assign a courier to an order via round-robin and notify them."""
    from django.core.cache import cache
    from apps.orders.courier_assignment import assign_courier_to_order

    cache_key = f"assign:courier:{order_id}"
    if not cache.add(cache_key, "processing", timeout=60):
        logger.info("Courier assignment already in progress for order %s", order_id)
        return

    try:
        courier_tg_id = assign_courier_to_order(order_id)
        if courier_tg_id is None:
            logger.info("No available courier for order %s, will retry via redispatch", order_id)
            cache.delete(cache_key)
            return

        send_courier_notification_task.delay(order_id, courier_tg_id)
        cache.set(cache_key, "assigned", timeout=_DEDUP_SENT_TTL)
    except Exception:
        cache.delete(cache_key)
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_courier_notification_task(self, order_id: int, courier_tg_id: int):
    """Send Telegram notification to assigned courier with retry."""
    from django.conf import settings as django_settings
    from apps.orders.models import Order
    from apps.notifications.models import CourierNotificationMessage

    bot_token = getattr(django_settings, "COURIER_BOT_TOKEN", "")
    if not bot_token:
        logger.warning("COURIER_BOT_TOKEN not configured; skipping courier notification")
        return

    order = Order.objects.filter(id=order_id).only("id", "total_price", "address").first()
    if not order:
        return

    total = int(order.total_price) if order.total_price == int(order.total_price) else float(order.total_price)
    text = (
        f"🔔 <b>Вам назначен заказ #{order_id}!</b>\n"
        f"💰 {total}₽"
    )
    if order.address:
        text += f"\n🏠 {order.address}"
    text += "\n\nНажмите /orders для подробностей."

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": courier_tg_id,
            "text": text,
            "parse_mode": "HTML",
        }, timeout=5)
        resp.raise_for_status()
        msg_data = resp.json()
        if msg_data.get("ok"):
            CourierNotificationMessage.objects.create(
                courier_tg_id=courier_tg_id,
                telegram_message_id=msg_data["result"]["message_id"],
            )
        logger.info("Courier notification sent for order #%s to courier %s", order_id, courier_tg_id)
    except requests.RequestException as e:
        logger.error("Courier notification failed for %s: %s", courier_tg_id, e)
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=0)
def redispatch_unassigned_orders(self):
    """Periodic task: try to assign couriers to unassigned ready orders."""
    from apps.orders.courier_assignment import get_unassigned_ready_orders

    order_ids = get_unassigned_ready_orders()
    if not order_ids:
        return

    logger.info("Redispatch: %d unassigned ready orders", len(order_ids))
    for oid in order_ids:
        assign_courier_task.delay(oid)
