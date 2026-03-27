from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.api.security import require_onec_auth

NOT_FOUND = "Card not found"


@csrf_exempt
@require_POST
@require_onec_auth
def onec_customer_check(request):
    from apps.loyalty.models import CustomUser

    raw = request.body or b""
    if not raw:
        return JsonResponse({"detail": "empty_body"}, status=400)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid_json"}, status=400)

    card_id = (str(data.get("card_id") or "")).strip() or None
    telegram_id = (str(data.get("telegram_id") or "")).strip() or None

    if not card_id and not telegram_id:
        return JsonResponse(
            {"detail": "card_id or telegram_id is required"}, status=400,
        )

    if card_id:
        user = CustomUser.objects.filter(card_id=card_id).first()
    else:
        user = CustomUser.objects.filter(telegram_id=telegram_id).first()

    if not user or not user.card_id:
        return JsonResponse({"card_id": NOT_FOUND})

    return JsonResponse({"card_id": user.card_id})
