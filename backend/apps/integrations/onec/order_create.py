from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.api.security import require_onec_auth
from apps.integrations.onec.utils import onec_error


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

    return JsonResponse(
        {
            "status": "ok",
            "order_id": order_id,
            "onec_guid": payload.get("onec_guid") or None,
        },
        status=200,
    )
