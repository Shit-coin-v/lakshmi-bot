"""Sync HTTP client for sending orders to 1C (used by Celery tasks).

Note (O4): This is the **sync** 1C client (requests-based), designed for
Celery tasks where retry is handled via ``self.retry()``. The async
counterpart lives in ``shared/clients/onec_client.py`` (aiohttp-based,
used in aiogram bot handlers with built-in backoff).
This split is intentional — different retry strategies and async contexts.
"""

import os
import random
import requests
import uuid
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone as dj_tz

from apps.orders.models import Order

logger = logging.getLogger(__name__)


def _get_onec_order_url() -> str | None:
    """Return 1C order URL or None if not configured (dev environment)."""
    url = getattr(settings, "ONEC_ORDER_URL", None) or getattr(settings, "ONEC_CUSTOMER_URL", None)
    if not url or url.startswith("CHANGE_ME"):
        return None
    return url


def send_order_to_onec_impl(self, order_id: int):
    # 1) Блокируем заказ и собираем payload в одной транзакции
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
        if not order.sync_idempotency_key:
            order.sync_idempotency_key = uuid.uuid4()
        order.save(update_fields=["sync_status", "sync_attempts", "last_sync_error", "sync_idempotency_key"])

        # Собираем payload внутри транзакции (items уже prefetch'нуты)
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
                "email": order.customer.email,
                "phone": order.phone,
                "full_name": order.customer.full_name,
            },
            "delivery": {
                "type": order.fulfillment_type,
                "address": order.address,
                "comment": order.comment,
            },
            "payment_method": order.payment_method,
            "fulfillment_type": order.fulfillment_type,
            "prices": {
                "products_price": str(order.products_price),
                "delivery_price": str(order.delivery_price),
                "total_price": str(order.total_price),
            },
            "store_id": store_id,
            "items": items,
        }

    # 4) Отправляем в 1С (или в твой proxy)
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": os.getenv("INTEGRATION_API_KEY", ""),
        "X-Idempotency-Key": str(order.sync_idempotency_key),
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        text = resp.text
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"HTTP {resp.status_code}: {text}")

        data = {}
        try:
            data = resp.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
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

    except (requests.RequestException, RuntimeError) as exc:
        logger.exception("send_order_to_onec failed: order_id=%s", order_id)
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            return {"status": "failed", "reason": str(exc)}

        if self.request.retries >= self.max_retries:
            _fail_order(order_id, str(exc))
            return {"status": "failed", "reason": str(exc)}

        base = min(20 + self.request.retries * 10, 70)
        countdown = base + random.uniform(0, base * 0.3)
        raise self.retry(exc=exc, countdown=countdown)


def _fail_order(order_id: int, err: str):
    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id)
        order.sync_status = "failed"
        order.last_sync_error = (err or "")[:4000]
        order.save(update_fields=["sync_status", "last_sync_error"])
