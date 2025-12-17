import os
import requests
import uuid
import logging

from datetime import date
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone as dj_tz

from celery import shared_task
from dotenv import load_dotenv

from main.models import CustomUser, Order

logger = logging.getLogger(__name__)


load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


@shared_task
def send_birthday_congratulations():
    today = date.today()
    birthday_users = CustomUser.objects.filter(birth_date__month=today.month, birth_date__day=today.day)

    for user in birthday_users:
        if not user.telegram_id:
            continue

        message = f"🎉 Поздравляем тебя с Днём Рождения, {user.full_name or 'друг'}! Желаем счастья, здоровья и успехов! 🎂"

        payload = {
            "chat_id": user.telegram_id,
            "text": message,
        }

        try:
            response = requests.post(BASE_URL, data=payload)
            response.raise_for_status()
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user.telegram_id}: {e}")

def _get_onec_order_url() -> str:
    url = getattr(settings, "ONEC_ORDER_URL", None) or getattr(settings, "ONEC_CUSTOMER_URL", None)
    if not url:
        raise RuntimeError("ONEC_ORDER_URL is not configured")
    return url


@shared_task(bind=True, max_retries=7, default_retry_delay=10)
def send_order_to_onec(self, order_id: int):
    # 1) Блокируем заказ, чтобы две задачи не отправили одно и то же
    with transaction.atomic():
        order = (
            Order.objects.select_for_update()
            .select_related("customer")
            .prefetch_related("items__product")
            .get(id=order_id)
        )

        # Уже отправлен — выходим (идемпотентность на нашей стороне)
        if order.sync_status == "sent" and order.sent_to_onec_at:
            return {"status": "already_sent", "order_id": order_id}

        order.sync_status = "queued"
        order.sync_attempts = (order.sync_attempts or 0) + 1
        order.last_sync_error = None
        order.save(update_fields=["sync_status", "sync_attempts", "last_sync_error"])

    # 2) Собираем payload
    items = []
    store_ids = set()

    for it in order.items.all():
        store_ids.add(getattr(it.product, "store_id", None))
        items.append(
            {
                "product_code": it.product.product_code,
                "name": it.product.name,
                "quantity": int(it.quantity),
                "price": str(it.price_at_moment),
                "line_total": str((it.price_at_moment * it.quantity)),
            }
        )

    store_ids.discard(None)
    if len(store_ids) > 1:
        # Заказ из нескольких магазинов — лучше фейлить сразу
        msg = f"Order contains multiple store_id values: {sorted(store_ids)}"
        _fail_order(order_id, msg)
        raise RuntimeError(msg)

    store_id = next(iter(store_ids), None)

    payload = {
        "order_id": order.id,
        "created_at": order.created_at.isoformat(),
        "customer": {
            "id": order.customer_id,
            "telegram_id": order.customer.telegram_id,
            "phone": order.phone,
            "full_name": order.customer.full_name,
        },
        "delivery": {
            "address": order.address,
            "comment": order.comment,
        },
        "payment_method": order.payment_method,
        "prices": {
            "products_price": str(order.products_price),
            "delivery_price": str(order.delivery_price),
            "total_price": str(order.total_price),
        },
        "store_id": store_id,
        "items": items,
    }

    # 3) Отправляем в 1С (или в твой proxy)
    url = _get_onec_order_url()
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": os.getenv("INTEGRATION_API_KEY", ""),
        "X-Idempotency-Key": str(uuid.uuid4()),
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        text = resp.text
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"HTTP {resp.status_code}: {text}")

        data = {}
        try:
            data = resp.json()
        except Exception:
            data = {"raw": text}

        onec_guid = data.get("onec_guid") or data.get("order_guid") or None

        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)
            order.sync_status = "sent"
            order.sent_to_onec_at = dj_tz.now()
            order.onec_guid = onec_guid or order.onec_guid
            order.last_sync_error = None
            order.save(update_fields=["sync_status", "sent_to_onec_at", "onec_guid", "last_sync_error"])

        return {"status": "sent", "order_id": order_id, "onec_guid": onec_guid}
    
    except Exception as exc:
        logger.exception("send_order_to_onec failed: order_id=%s", order_id)
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            return {"status": "failed", "reason": str(exc)}

        raise self.retry(exc=exc)


def _fail_order(order_id: int, err: str):
    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id)
        order.sync_status = "failed"
        order.last_sync_error = (err or "")[:4000]
        order.save(update_fields=["sync_status", "last_sync_error"])
