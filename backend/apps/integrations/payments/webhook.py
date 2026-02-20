"""ЮKassa webhook handler.

Receives payment events and updates order status accordingly.
"""

from __future__ import annotations

import json
import logging

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

# ЮKassa webhook IP ranges (for optional IP filtering)
YUKASSA_IP_RANGES = [
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.156.11",
    "77.75.156.35",
    "77.75.154.128/25",
    "2a02:5180::/32",
]


@csrf_exempt
@require_POST
def yukassa_webhook(request):
    """Handle ЮKassa webhook notifications."""
    from apps.orders.models import Order
    from apps.notifications.tasks import notify_pickers_new_order, send_order_push_task
    from apps.integrations.onec.tasks import send_order_to_onec

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "invalid json"}, status=400)

    event_type = body.get("event")
    payment_obj = body.get("object", {})
    payment_id = payment_obj.get("id")

    if not payment_id:
        return JsonResponse({"error": "no payment id"}, status=400)

    logger.info("YooKassa webhook: event=%s payment_id=%s", event_type, payment_id)

    if event_type == "payment.waiting_for_capture":
        # Payment authorized (hold) — activate the order
        _handle_authorized(payment_id, Order, notify_pickers_new_order, send_order_to_onec, send_order_push_task)

    elif event_type == "payment.canceled":
        # Payment canceled by user or timeout
        _handle_payment_canceled(payment_id, Order, send_order_push_task)

    elif event_type == "payment.succeeded":
        # For capture=true payments (not our flow, but handle gracefully)
        logger.info("YooKassa payment.succeeded for %s (unexpected for hold flow)", payment_id)

    # Always return 200 to ЮKassa
    return JsonResponse({"status": "ok"})


def _handle_authorized(payment_id, Order, notify_pickers_new_order, send_order_to_onec, send_order_push_task):
    """Payment authorized — order can proceed."""
    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(payment_id=payment_id)
        except Order.DoesNotExist:
            logger.error("Webhook: order not found for payment_id=%s", payment_id)
            return

        if order.payment_status != "pending":
            logger.info("Webhook: order %s already payment_status=%s, skip", order.id, order.payment_status)
            return

        order.payment_status = "authorized"
        order._skip_signal_notification = True
        order.save(update_fields=["payment_status"])

    # Outside transaction: trigger notifications
    oid = order.id
    send_order_to_onec.delay(oid)
    notify_pickers_new_order.delay(oid)
    send_order_push_task.delay(oid, "new", "new")  # push: "Оплата прошла, заказ принят"

    logger.info("Webhook: order %s authorized, notifications sent", oid)


def _handle_payment_canceled(payment_id, Order, send_order_push_task):
    """Payment canceled — cancel the order."""
    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(payment_id=payment_id)
        except Order.DoesNotExist:
            logger.error("Webhook: order not found for payment_id=%s", payment_id)
            return

        if order.payment_status in ("canceled", "failed"):
            logger.info("Webhook: order %s already %s, skip", order.id, order.payment_status)
            return

        prev_status = order.status
        order.payment_status = "canceled"
        order.status = "canceled"
        order._skip_signal_notification = True
        order.save(update_fields=["payment_status", "status"])

    oid = order.id
    send_order_push_task.delay(oid, prev_status, "canceled")
    logger.info("Webhook: order %s canceled due to payment cancellation", oid)
