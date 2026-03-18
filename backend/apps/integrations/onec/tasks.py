import logging
import os
import random
from datetime import timedelta

import requests
from celery import shared_task
from django.utils import timezone

from .order_sync import _get_onec_order_url, send_order_to_onec_impl

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5)
def send_order_to_onec(self, order_id: int):
    """Send order to 1C ERP system."""
    return send_order_to_onec_impl(self, order_id)


@shared_task(bind=True, max_retries=5)
def notify_onec_order_canceled(self, order_id: int):
    """Notify 1C that an order has been canceled (with reason and payment result)."""
    from apps.orders.models import Order

    url = _get_onec_order_url()
    if not url:
        logger.info("notify_onec_order_canceled: ONEC_ORDER_URL not configured, skipping.")
        return {"status": "skipped", "reason": "no_url"}

    try:
        order = Order.objects.select_related("customer").get(id=order_id)
    except Order.DoesNotExist:
        logger.error("notify_onec_order_canceled: order %s not found", order_id)
        return {"status": "failed", "reason": "order_not_found"}

    # Determine payment result
    payment_result = "no_online_payment"
    if order.payment_id:
        ps = order.payment_status
        if ps == "canceled":
            payment_result = "hold_canceled"
        elif ps == "failed":
            payment_result = "refunded"
        elif ps in ("authorized", "captured"):
            payment_result = "refund_pending"
        else:
            payment_result = ps

    payload = {
        "order_id": order.id,
        "status": "canceled",
        "cancel_reason": order.cancel_reason,
        "canceled_by": order.canceled_by,
        "payment_method": order.payment_method,
        "payment_id": order.payment_id,
        "payment_result": payment_result,
        "courier_telegram_id": order.delivered_by,
    }

    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": os.getenv("INTEGRATION_API_KEY", ""),
    }

    onec_user = os.getenv("ONEC_BASIC_AUTH_USER", "")
    if onec_user:
        import base64
        onec_pass = os.getenv("ONEC_BASIC_AUTH_PASSWORD", "")
        credentials = base64.b64encode(f"{onec_user}:{onec_pass}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {credentials}"

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")

        logger.info("notify_onec_order_canceled: order %s notified successfully", order_id)
        return {"status": "sent", "order_id": order_id}

    except (requests.RequestException, RuntimeError) as exc:
        logger.exception("notify_onec_order_canceled failed: order_id=%s", order_id)

        from django.conf import settings
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            return {"status": "failed", "reason": str(exc)}

        if self.request.retries >= self.max_retries:
            return {"status": "failed", "reason": str(exc)}

        base = min(20 + self.request.retries * 10, 70)
        countdown = base + random.uniform(0, base * 0.3)
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(bind=True, max_retries=5)
def notify_onec_order_completed(self, order_id: int):
    """Notify 1C that an order has been delivered (completed)."""
    from apps.orders.models import Order

    url = _get_onec_order_url()
    if not url:
        logger.info("notify_onec_order_completed: ONEC_ORDER_URL not configured, skipping.")
        return {"status": "skipped", "reason": "no_url"}

    try:
        order = Order.objects.select_related("customer").get(id=order_id)
    except Order.DoesNotExist:
        logger.error("notify_onec_order_completed: order %s not found", order_id)
        return {"status": "failed", "reason": "order_not_found"}

    payload = {
        "order_id": order.id,
        "status": "completed",
        "payment_method": order.payment_method,
        "payment_id": order.payment_id,
        "payment_status": order.payment_status,
        "courier_telegram_id": order.delivered_by,
    }

    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": os.getenv("INTEGRATION_API_KEY", ""),
    }

    onec_user = os.getenv("ONEC_BASIC_AUTH_USER", "")
    if onec_user:
        import base64
        onec_pass = os.getenv("ONEC_BASIC_AUTH_PASSWORD", "")
        credentials = base64.b64encode(f"{onec_user}:{onec_pass}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {credentials}"

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")

        logger.info("notify_onec_order_completed: order %s notified successfully", order_id)
        return {"status": "sent", "order_id": order_id}

    except (requests.RequestException, RuntimeError) as exc:
        logger.exception("notify_onec_order_completed failed: order_id=%s", order_id)

        from django.conf import settings
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            return {"status": "failed", "reason": str(exc)}

        if self.request.retries >= self.max_retries:
            return {"status": "failed", "reason": str(exc)}

        base = min(20 + self.request.retries * 10, 70)
        countdown = base + random.uniform(0, base * 0.3)
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(bind=True, max_retries=0)
def rollback_stuck_assembly_orders(self):
    """Periodic: rollback orders stuck in 'assembly' without 1C confirmation.

    When 1C fetches pending orders via GET /onec/orders/pending, the endpoint
    sets status='assembly'. If 1C crashes before processing, orders stay in
    'assembly' forever. This task rolls them back to 'new' after a timeout.
    """
    from apps.orders.models import Order

    timeout_minutes = 10
    cutoff = timezone.now() - timedelta(minutes=timeout_minutes)

    stuck_ids = list(
        Order.objects.filter(
            status="assembly",
            assembled_by__isnull=True,
            onec_guid__isnull=True,
            created_at__lt=cutoff,
        ).values_list("id", flat=True)
    )

    if not stuck_ids:
        return

    count = Order.objects.filter(
        id__in=stuck_ids, status="assembly",
    ).update(status="new")

    logger.info(
        "rollback_stuck_assembly_orders: rolled back %d/%d orders to 'new'",
        count, len(stuck_ids),
    )
