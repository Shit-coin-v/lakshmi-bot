"""ЮKassa webhook handler.

Receives payment events and updates order status accordingly.
IP filtering: only accepts requests from ЮKassa IP ranges.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import os

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.common.security import _client_ip

logger = logging.getLogger(__name__)

# ЮKassa webhook IP ranges (official docs)
_YUKASSA_IP_RANGES = [
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.156.11/32",
    "77.75.156.35/32",
    "77.75.154.128/25",
    "2a02:5180::/32",
]

_YUKASSA_NETWORKS = [ipaddress.ip_network(r) for r in _YUKASSA_IP_RANGES]

_DISABLE_IP_CHECK = os.getenv("YUKASSA_DISABLE_IP_CHECK", "").lower() in ("1", "true")


def _is_yukassa_ip(request) -> bool:
    """Check if request comes from ЮKassa IP range."""
    if _DISABLE_IP_CHECK:
        return True
    try:
        addr = ipaddress.ip_address(_client_ip(request))
    except ValueError:
        return False
    return any(addr in net for net in _YUKASSA_NETWORKS)


@csrf_exempt
@require_POST
def yukassa_webhook(request):
    """Handle ЮKassa webhook notifications."""
    if not _is_yukassa_ip(request):
        logger.warning(
            "YooKassa webhook rejected: ip=%s path=%s",
            _client_ip(request), request.path,
        )
        return JsonResponse({"error": "forbidden"}, status=403)
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

        oid = order.id
        transaction.on_commit(lambda: send_order_to_onec.delay(oid))
        transaction.on_commit(lambda: notify_pickers_new_order.delay(oid))
        transaction.on_commit(lambda: send_order_push_task.delay(oid, "pending_payment", "new"))

    logger.info("Webhook: order %s authorized, notifications scheduled", order.id)


def _handle_payment_canceled(payment_id, Order, send_order_push_task):
    """Payment canceled — cancel the order (if not already in delivery+)."""
    _NON_CANCELLABLE = ("delivery", "arrived", "completed")

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

        if order.status in _NON_CANCELLABLE:
            # Order already handed to courier/delivered — don't cancel order,
            # only update payment_status (reflects ЮKassa reality)
            logger.warning(
                "Webhook: payment canceled but order %s is in status=%s, "
                "not canceling order (manual check required)",
                order.id, order.status,
            )
            order.manual_check_required = True
            order._skip_signal_notification = True
            order.save(update_fields=["payment_status", "manual_check_required"])
        else:
            order.status = "canceled"
            order._skip_signal_notification = True
            order.save(update_fields=["payment_status", "status"])

        oid = order.id
        if prev_status not in _NON_CANCELLABLE:
            transaction.on_commit(lambda: send_order_push_task.delay(oid, prev_status, "canceled"))

    logger.info("Webhook: order %s payment canceled (order_status=%s)", order.id, order.status)
