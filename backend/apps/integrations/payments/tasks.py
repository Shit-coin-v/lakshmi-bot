"""Celery tasks for ЮKassa payment operations.

Retry strategy (two levels):
  1. HTTP-level: 2 attempts, 1s+2s delay (transient network errors only)
  2. Celery-level: exponential backoff with jitter

capture: 5 retries, 10→20→40→80→160s (max 300s), TTL 30 min
cancel:  4 retries, 5→15→30→60s, with jitter ±20%
"""

from __future__ import annotations

import logging
import random
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# capture TTL: stop retrying after 30 minutes from first attempt
_CAPTURE_TTL_MINUTES = 30

# Celery retry delays (base, before jitter)
_CAPTURE_DELAYS = [10, 20, 40, 80, 160]  # max capped to 300s
_CANCEL_DELAYS = [5, 15, 30, 60]

_MAX_CELERY_DELAY = 300  # 5 minutes


def _finalize_ttl_expired(order_id: int, Order) -> None:
    """Handle TTL expiration for capture: check remote status before giving up.

    Instead of blindly marking as failed, checks ЮKassa for actual status:
    - succeeded → update locally as captured
    - canceled → update locally as canceled
    - other / unreachable → set manual_check_required=True (not failed)
    """
    from apps.integrations.payments.yukassa_client import get_payment

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return

    if order.payment_status not in ("authorized",):
        return

    try:
        remote = get_payment(order.payment_id)
        remote_status = remote.get("status")

        if remote_status == "succeeded":
            order.payment_status = "captured"
            order.save(update_fields=["payment_status"])
            logger.info(
                "TTL expired but payment already captured for order %s", order_id,
            )
            return

        if remote_status == "canceled":
            order.payment_status = "canceled"
            order.save(update_fields=["payment_status"])
            logger.info(
                "TTL expired, payment was canceled for order %s", order_id,
            )
            return

        # Unknown/pending status — need manual review
        order.manual_check_required = True
        order.save(update_fields=["manual_check_required"])
        logger.warning(
            "TTL expired for order %s, remote status=%s — flagged for manual check",
            order_id, remote_status,
        )

    except Exception:
        # Can't reach ЮKassa — flag for manual review, don't assume failed
        order.manual_check_required = True
        order.save(update_fields=["manual_check_required"])
        logger.exception(
            "TTL expired for order %s, failed to check remote status — flagged for manual check",
            order_id,
        )


def _jitter(base_delay: float, factor: float = 0.2) -> float:
    """Add ±factor random jitter to delay."""
    jitter = base_delay * factor * random.uniform(-1, 1)
    return max(1, base_delay + jitter)


@shared_task(bind=True, max_retries=5)
def capture_payment_task(self, order_id: int, first_attempt_at: str | None = None):
    """Capture (finalize) an authorized payment after delivery.

    Retries with exponential backoff: 10s, 20s, 40s, 80s, 160s (max 300s).
    TTL: 30 minutes from first attempt — after that, mark as failed.
    """
    from apps.orders.models import Order
    from apps.integrations.payments.yukassa_client import (
        capture_payment, get_payment, YukassaLogicalError,
    )

    now = timezone.now()

    # Track TTL from first attempt
    if first_attempt_at is None:
        first_attempt_at = now.isoformat()
    else:
        first_time = timezone.datetime.fromisoformat(first_attempt_at)
        if (now - first_time) > timedelta(minutes=_CAPTURE_TTL_MINUTES):
            logger.error(
                "capture_payment_task: TTL exceeded for order %s (started %s)",
                order_id, first_attempt_at,
            )
            _finalize_ttl_expired(order_id, Order)
            return

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.error("capture_payment_task: order %s not found", order_id)
        return

    # Idempotency: skip if already captured or not in expected state
    if order.payment_status != "authorized":
        logger.info(
            "capture_payment_task: order %s payment_status=%s, skip",
            order_id, order.payment_status,
        )
        return

    if not order.payment_id:
        logger.error("capture_payment_task: order %s has no payment_id", order_id)
        return

    try:
        # Check current payment status at ЮKassa (idempotency)
        remote = get_payment(order.payment_id)
        if remote["status"] == "succeeded":
            # Already captured
            order.payment_status = "captured"
            order.save(update_fields=["payment_status"])
            logger.info("Payment already captured for order %s", order_id)
            return
        if remote["status"] == "canceled":
            order.payment_status = "canceled"
            order.save(update_fields=["payment_status"])
            logger.warning("Payment was canceled externally for order %s", order_id)
            return

        result = capture_payment(
            order.payment_id, order.total_price,
            idempotency_key=f"capture-{order_id}",
        )
        if result["status"] == "succeeded":
            order.payment_status = "captured"
            order.save(update_fields=["payment_status"])
            logger.info("Payment captured for order %s", order_id)
        else:
            logger.warning(
                "Unexpected capture status for order %s: %s",
                order_id, result["status"],
            )

    except YukassaLogicalError as exc:
        # Logical error (4xx) — do not retry
        logger.error("Capture logical error for order %s: %s", order_id, exc)
        order.payment_status = "failed"
        order.save(update_fields=["payment_status"])

    except Exception as exc:
        retry_num = self.request.retries
        if retry_num < self.max_retries:
            base_delay = _CAPTURE_DELAYS[min(retry_num, len(_CAPTURE_DELAYS) - 1)]
            delay = min(_jitter(base_delay), _MAX_CELERY_DELAY)
            logger.warning(
                "capture_payment_task retry %d/%d for order %s in %.0fs: %s",
                retry_num + 1, self.max_retries, order_id, delay, exc,
            )
            raise self.retry(
                exc=exc,
                countdown=delay,
                kwargs={"order_id": order_id, "first_attempt_at": first_attempt_at},
            )
        else:
            logger.exception(
                "capture_payment_task: all retries exhausted for order %s", order_id,
            )
            order.payment_status = "failed"
            order.save(update_fields=["payment_status"])


@shared_task(bind=True, max_retries=4)
def cancel_payment_task(self, order_id: int):
    """Cancel or refund a payment when order is canceled.

    Retries: 4 attempts, delays 5s→15s→30s→60s with ±20% jitter.
    """
    from apps.orders.models import Order
    from apps.integrations.payments.yukassa_client import (
        cancel_payment, create_refund, get_payment, YukassaLogicalError,
    )

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.error("cancel_payment_task: order %s not found", order_id)
        return

    if not order.payment_id:
        return

    # Idempotency: skip if already canceled
    if order.payment_status in ("canceled", "failed", "none"):
        logger.info(
            "cancel_payment_task: order %s payment_status=%s, nothing to do",
            order_id, order.payment_status,
        )
        return

    try:
        # Check remote status first (idempotency)
        remote = get_payment(order.payment_id)
        if remote["status"] == "canceled":
            order.payment_status = "canceled"
            order.save(update_fields=["payment_status"])
            logger.info("Payment already canceled for order %s", order_id)
            return

        if order.payment_status == "authorized":
            # Hold → cancel
            result = cancel_payment(
                order.payment_id,
                idempotency_key=f"cancel-{order_id}",
            )
            order.payment_status = "canceled"
            order.save(update_fields=["payment_status"])
            logger.info(
                "Payment canceled (hold) for order %s: %s",
                order_id, result["status"],
            )

        elif order.payment_status == "captured":
            # Already captured → refund
            result = create_refund(
                order.payment_id, order.total_price,
                idempotency_key=f"refund-{order_id}",
            )
            order.payment_status = "canceled"
            order.save(update_fields=["payment_status"])
            logger.info(
                "Payment refunded for order %s: %s",
                order_id, result["status"],
            )

    except YukassaLogicalError as exc:
        # Logical error — do not retry
        logger.error("Cancel logical error for order %s: %s", order_id, exc)

    except Exception as exc:
        retry_num = self.request.retries
        if retry_num < self.max_retries:
            base_delay = _CANCEL_DELAYS[min(retry_num, len(_CANCEL_DELAYS) - 1)]
            delay = _jitter(base_delay)
            logger.warning(
                "cancel_payment_task retry %d/%d for order %s in %.0fs: %s",
                retry_num + 1, self.max_retries, order_id, delay, exc,
            )
            raise self.retry(exc=exc, countdown=delay)
        else:
            logger.exception(
                "cancel_payment_task: all retries exhausted for order %s", order_id,
            )


@shared_task(bind=True, max_retries=0)
def expire_pending_payments(self):
    """Periodic: cancel orders with pending payments older than timeout."""
    from django.conf import settings as django_settings
    from apps.orders.models import Order
    from apps.notifications.tasks import send_order_push_task

    timeout_minutes = getattr(django_settings, "YUKASSA_PAYMENT_TIMEOUT_MINUTES", 15)
    cutoff = timezone.now() - timedelta(minutes=timeout_minutes)

    expired_ids = list(
        Order.objects.filter(
            payment_status="pending",
            payment_method="sbp",
            created_at__lt=cutoff,
        ).values_list("id", flat=True)
    )

    if not expired_ids:
        return

    Order.objects.filter(id__in=expired_ids).update(
        payment_status="failed", status="canceled"
    )

    for oid in expired_ids:
        send_order_push_task.delay(oid, "new", "canceled")

    # Notify 1C about canceled orders that were already synced
    from apps.integrations.onec.tasks import notify_onec_order_canceled
    from django.db.models import Q
    synced_ids = list(
        Order.objects.filter(id__in=expired_ids).filter(
            Q(onec_guid__isnull=False) | Q(sync_status__in=("sent", "confirmed"))
        ).values_list("id", flat=True)
    )
    for oid in synced_ids:
        notify_onec_order_canceled.delay(oid)

    logger.info("expire_pending_payments: canceled %d orders", len(expired_ids))
