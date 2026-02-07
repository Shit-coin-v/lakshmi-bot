from __future__ import annotations

import json
import logging

from django.db import transaction as db_tx
from django.http import JsonResponse
from django.utils import timezone as dj_tz
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.api.security import require_onec_auth
from apps.integrations.onec.utils import onec_error

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
@require_onec_auth
def onec_order_status(request):
    from apps.orders.models import Order
    from apps.notifications.push import notify_order_status_change

    raw = request.body or b"{}"
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return onec_error("invalid_json", "Request body must be valid JSON.")

    order_id = payload.get("order_id")
    status_in = (payload.get("status") or "").strip()
    onec_guid = (payload.get("onec_guid") or "").strip() or None

    if not order_id:
        return onec_error(
            "missing_field",
            "order_id is required.",
            details={"order_id": ["required"]},
        )

    allowed = {"new", "assembly", "delivery", "completed", "canceled"}
    if status_in and status_in not in allowed:
        return onec_error(
            "invalid_status",
            "Invalid status value.",
            details={"status": sorted(allowed)},
        )

    try:
        with db_tx.atomic():
            o = Order.objects.select_for_update().get(id=int(order_id))

            updates: list[str] = []
            status_changed = False
            previous_status = o.status

            if status_in and o.status != status_in:
                o.status = status_in
                updates.append("status")
                status_changed = True

            if onec_guid and hasattr(o, "onec_guid") and o.onec_guid != onec_guid:
                o.onec_guid = onec_guid
                updates.append("onec_guid")

            if hasattr(o, "sync_status") and o.sync_status != "sent":
                o.sync_status = "sent"
                updates.append("sync_status")

            if hasattr(o, "sent_to_onec_at") and not o.sent_to_onec_at:
                o.sent_to_onec_at = dj_tz.now()
                updates.append("sent_to_onec_at")

            if hasattr(o, "last_sync_error") and o.last_sync_error:
                o.last_sync_error = None
                updates.append("last_sync_error")

            if updates:
                if status_changed:
                    # если у тебя где-то есть signal/observer — можно им управлять этим флагом
                    o._skip_signal_notification = True
                o.save(update_fields=updates)

            # ✅ ВАЖНО: пуш не должен ломать эндпоинт статуса
            if status_changed:
                try:
                    notify_order_status_change(o, previous_status=previous_status)
                except Exception:  # pragma: no cover — defensive: push must not break status endpoint
                    logger.exception(
                        "Failed to send push for order status change: order_id=%s %s->%s",
                        o.id,
                        previous_status,
                        o.status,
                    )

    except Order.DoesNotExist:
        return onec_error(
            "order_not_found",
            "Order not found.",
            details={"order_id": order_id},
            status_code=404,
        )
    except (TypeError, ValueError):
        return onec_error(
            "invalid_order_id",
            "order_id must be an integer.",
            details={"order_id": order_id},
        )

    return JsonResponse(
        {
            "status": "ok",
            "order": {"order_id": int(order_id), "status": status_in or None, "onec_guid": onec_guid},
        },
        status=200,
    )
