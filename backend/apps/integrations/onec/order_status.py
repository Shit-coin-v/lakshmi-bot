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
from apps.orders.services import (
    VALID_STATUSES,
    AlreadyAccepted,
    InvalidTransition,
    update_order_status,
)

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
@require_onec_auth
def onec_order_status(request):
    from apps.orders.models import Order

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
    courier_id = payload.get("courier_id")
    assembler_id = payload.get("assembler_id")

    if not order_id:
        return onec_error(
            "missing_field",
            "order_id is required.",
            details={"order_id": ["required"]},
        )

    if status_in and status_in not in VALID_STATUSES:
        return onec_error(
            "invalid_status",
            "Invalid status value.",
            details={"status": sorted(VALID_STATUSES)},
        )

    cancel_reason = (payload.get("cancel_reason") or "").strip() or None

    try:
        with db_tx.atomic():
            o, previous_status = update_order_status(
                order_id=int(order_id),
                new_status=status_in,
                assembler_id=int(assembler_id) if assembler_id is not None else None,
                courier_id=int(courier_id) if courier_id is not None else None,
                cancel_reason=cancel_reason,
                canceled_by="onec" if status_in == "canceled" else None,
            )

            # --- 1C-specific fields (not part of core service) ---
            onec_updates: list[str] = []

            if onec_guid and hasattr(o, "onec_guid") and o.onec_guid != onec_guid:
                o.onec_guid = onec_guid
                onec_updates.append("onec_guid")

            if hasattr(o, "sync_status") and o.sync_status != "sent":
                o.sync_status = "sent"
                onec_updates.append("sync_status")

            if hasattr(o, "sent_to_onec_at") and not o.sent_to_onec_at:
                o.sent_to_onec_at = dj_tz.now()
                onec_updates.append("sent_to_onec_at")

            if hasattr(o, "last_sync_error") and o.last_sync_error:
                o.last_sync_error = None
                onec_updates.append("last_sync_error")

            if onec_updates:
                o.save(update_fields=onec_updates)

    except InvalidTransition as exc:
        logger.warning(
            "Invalid transition %s → %s for order %s",
            exc.current, exc.target, order_id,
        )
        return onec_error(
            "invalid_transition",
            f"Transition {exc.current} → {exc.target} is not allowed.",
            status_code=409,
        )
    except AlreadyAccepted as exc:
        return onec_error(
            "already_accepted",
            f"Order already accepted by assembler {exc.assembled_by}.",
            status_code=409,
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
