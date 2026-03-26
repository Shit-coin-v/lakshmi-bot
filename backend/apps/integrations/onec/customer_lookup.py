"""1C endpoint: reverse lookup — telegram_id → card_id."""
from __future__ import annotations

import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.api.security import require_onec_auth
from apps.integrations.onec.utils import onec_error

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
@require_onec_auth
def onec_customer_lookup(request):
    from apps.main.models import CustomUser

    raw = request.body
    if not raw:
        return onec_error("invalid_json", "Request body must not be empty.")

    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return onec_error("invalid_json", "Request body must be valid JSON.")

    if not isinstance(data, dict):
        return onec_error("invalid_json", "Request body must be a JSON object.")

    telegram_id = data.get("telegram_id")

    if telegram_id is None:
        return onec_error(
            "missing_field",
            "telegram_id is required.",
            details={"telegram_id": ["required"]},
        )

    if isinstance(telegram_id, bool):
        return onec_error(
            "invalid_field",
            "telegram_id must be an integer or numeric string.",
            details={"telegram_id": ["invalid"]},
        )

    if isinstance(telegram_id, str):
        try:
            telegram_id = int(telegram_id)
        except ValueError:
            return onec_error(
                "invalid_field",
                "telegram_id must be an integer or numeric string.",
                details={"telegram_id": ["invalid"]},
            )
    elif not isinstance(telegram_id, int):
        return onec_error(
            "invalid_field",
            "telegram_id must be an integer or numeric string.",
            details={"telegram_id": ["invalid"]},
        )

    user = CustomUser.objects.filter(telegram_id=telegram_id).first()
    if not user:
        return onec_error(
            "customer_not_found",
            "Customer with this telegram_id not found.",
            status_code=404,
        )

    if not user.card_id:
        logger.warning("customer_lookup: user %s has no card_id", user.pk)
        return onec_error(
            "card_id_not_assigned",
            "Customer exists but card_id is not assigned.",
            status_code=404,
        )

    return JsonResponse({"status": "ok", "card_id": user.card_id})
