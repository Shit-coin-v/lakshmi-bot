from __future__ import annotations

import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.api.security import require_onec_auth
from apps.integrations.onec.utils import onec_error
from apps.orders.models import Order

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
@require_onec_auth
def onec_order_create(request):
    raw = request.body or b"{}"
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return onec_error("invalid_json", "Request body must be valid JSON.")

    order_id = payload.get("order_id")
    if not order_id:
        return onec_error("missing_field", "order_id is required.", details={"order_id": ["required"]})

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return onec_error("order_not_found", f"Order {order_id} not found.", status_code=404)

    onec_guid = payload.get("onec_guid")
    update_fields = []

    if onec_guid and onec_guid != order.onec_guid:
        order.onec_guid = onec_guid
        update_fields.append("onec_guid")

    if order.sync_status in ("new", "queued", "sent"):
        order.sync_status = "confirmed"
        update_fields.append("sync_status")

    if update_fields:
        order.save(update_fields=update_fields)
        logger.info("onec_order_create: order %s updated (fields=%s, onec_guid=%s)", order_id, update_fields, onec_guid)

    return JsonResponse(
        {
            "status": "ok",
            "order_id": order_id,
            "onec_guid": order.onec_guid,
        },
        status=200,
    )
