from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal as D
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone as dj_tz
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.api.security import require_onec_auth


def _as_decimal(value: Any) -> D:
    if isinstance(value, D):
        return value
    return D(str(value))


@csrf_exempt
@require_POST
@require_onec_auth
def onec_customer_sync(request):
    from apps.api.models import OneCClientMap
    from apps.loyalty.models import CustomUser

    raw = request.body or b""
    if not raw:
        return JsonResponse({"detail": "empty_body"}, status=400)
    try:
        payload_str = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw
        data = json.loads(payload_str)
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid_json"}, status=400)

    telegram_raw = data.get("telegram_id")
    qr_code = str(data.get("qr_code") or "").strip()
    email_raw = data.get("email")
    email = (email_raw or "").strip().lower() or None

    telegram_id: int | None
    if telegram_raw in (None, "", False):
        telegram_id = None
    else:
        try:
            telegram_id = int(telegram_raw)
        except (TypeError, ValueError):
            return JsonResponse({"detail": {"telegram_id": ["Неверное значение"]}}, status=400)

    if telegram_id is None and not qr_code and not email:
        return JsonResponse({"detail": {"identifier": ["Нужно указать telegram_id, qr_code или email."]}}, status=400)

    user: CustomUser | None = None
    if qr_code:
        qr_norm = qr_code.strip()

    # If full URL received — extract path only
        if qr_norm.startswith("http://") or qr_norm.startswith("https://"):
            try:
                qr_norm = urlparse(qr_norm).path or qr_norm
            except (ValueError, AttributeError):
                pass

    # Sometimes arrives without leading "/"
        if qr_norm.startswith("media/"):
            qr_norm = "/" + qr_norm

        user = CustomUser.objects.filter(qr_code=qr_norm).first()

    # Fallback: if QR is just digits (telegram_id)
        if not user and qr_norm.isdigit():
            user = CustomUser.objects.filter(telegram_id=int(qr_norm)).first()

        if not user:
            return JsonResponse({"detail": {"qr_code": ["Пользователь не найден"]}}, status=404)


    if telegram_id is not None:
        user_by_tid = CustomUser.objects.filter(telegram_id=telegram_id).first()
        if not user_by_tid:
            return JsonResponse({"detail": {"telegram_id": ["Пользователь не найден"]}}, status=404)
        if user and user_by_tid.id != user.id:
            return JsonResponse({"detail": {"telegram_id": ["Не совпадает с QR-кодом"]}}, status=400)
        user = user or user_by_tid

    if email:
        email_qs = CustomUser.objects.filter(email__iexact=email)
        email_count = email_qs.count()
        if email_count == 0:
            if not user:
                return JsonResponse({"detail": {"email": ["Пользователь не найден"]}}, status=404)
        elif email_count > 1:
            return JsonResponse({"detail": {"email": ["Найдено несколько пользователей с таким email"]}}, status=409)
        else:
            user_by_email = email_qs.first()
            if user and user_by_email.id != user.id:
                return JsonResponse({"detail": {"email": ["Не совпадает с другим идентификатором"]}}, status=400)
            user = user or user_by_email

    if not user:
        return JsonResponse({"detail": {"qr_code": ["Пользователь не найден"]}}, status=404)

    if telegram_id is None:
        telegram_id = user.telegram_id

    one_c_guid = str(data.get("one_c_guid") or "")
    bonus_balance = data.get("bonus_balance")
    referrer_tid = data.get("referrer_telegram_id")

    write_mode = any([bonus_balance is not None, referrer_tid, one_c_guid])

    raw_dt = data.get("created_at") or data.get("registration_date")
    if raw_dt:
        try:
            dt = datetime.fromisoformat(str(raw_dt).replace("Z", "+00:00"))
        except ValueError:
            return JsonResponse({"detail": {"created_at": ["Неверный формат datetime"]}}, status=400)
        if dj_tz.is_naive(dt):
            dt_aware = dj_tz.make_aware(dt, timezone=timezone.utc)
        else:
            dt_aware = dt.astimezone(timezone.utc)
    else:
        dt_aware = datetime.now(timezone.utc)
    dt_naive = dj_tz.make_naive(dt_aware, timezone=timezone.utc)

    if bonus_balance is not None:
        try:
            user.bonuses = _as_decimal(bonus_balance)
        except (ValueError, TypeError, ArithmeticError):
            return JsonResponse({"detail": {"bonus_balance": ["Неверное число"]}}, status=400)

    if referrer_tid:
        try:
            ref_tid = int(referrer_tid)
        except (TypeError, ValueError):
            ref_tid = None
        if ref_tid and ref_tid != telegram_id and not getattr(user, "referrer", None):
            ref_user = CustomUser.objects.filter(telegram_id=ref_tid).first()
            if ref_user:
                user.referrer = ref_user

    if hasattr(user, "created_at") and not user.created_at:
        user.created_at = dt_aware if settings.USE_TZ else dt_naive

    if write_mode:
        update_fields = []
        if bonus_balance is not None:
            update_fields.append("bonuses")
        if referrer_tid and getattr(user, "referrer", None):
            update_fields.append("referrer")
        if hasattr(user, "created_at") and user.created_at:
            update_fields.append("created_at")
        if update_fields:
            user.save(update_fields=update_fields)

    if one_c_guid:
        OneCClientMap.objects.update_or_create(one_c_guid=one_c_guid, defaults={"user": user})

    mapping = OneCClientMap.objects.filter(user=user).first()
    guid_for_resp = getattr(mapping, "one_c_guid", None) or (one_c_guid or None)

    return JsonResponse(
        {
            "status": "ok" if write_mode else "lookup",
            "customer": {
                "telegram_id": user.telegram_id,
                "id": user.id,
                "one_c_guid": guid_for_resp,
                "qr_code": user.qr_code,
                "email": user.email,
                "bonus_balance": float(user.bonuses or 0),
                "referrer_telegram_id": getattr(getattr(user, "referrer", None), "telegram_id", None),
            },
        }
    )
