"""REST and webhook views exposed by the backend API."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal as D, ROUND_HALF_UP
from typing import Any

import requests
from django.conf import settings
from django.db import IntegrityError, transaction as db_tx
from django.http import JsonResponse
from django.utils import timezone as dj_tz
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import CustomUser, Product, Transaction
from src import config

from .models import OneCClientMap
from .security import require_onec_auth
from .serializers import (
    ProductUpdateSerializer,
    PurchaseSerializer,
    ReceiptSerializer,
)

logger = logging.getLogger(__name__)


def _as_decimal(value: Any) -> D:
    if isinstance(value, D):
        return value
    return D(str(value))


def _quantize(amount: D) -> D:
    return amount.quantize(D("0.01"), rounding=ROUND_HALF_UP)


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(require_onec_auth, name="dispatch")
class PurchaseAPIView(APIView):
    """Simplified webhook for legacy purchase notifications."""

    def post(self, request):
        serializer = PurchaseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        telegram_id = data["telegram_id"]
        try:
            customer = CustomUser.objects.get(telegram_id=telegram_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        purchase_dt = datetime.combine(data["purchase_date"], data["purchase_time"])
        if settings.USE_TZ and dj_tz.is_naive(purchase_dt):
            purchase_dt = dj_tz.make_aware(purchase_dt, timezone=timezone.utc)

        customer.bonuses = data["total_bonuses"]
        customer.last_purchase_date = purchase_dt
        customer.total_spent = (customer.total_spent or D("0")) + data["total"]
        customer.purchase_count = (customer.purchase_count or 0) + 1
        customer.save(
            update_fields=[
                "bonuses",
                "last_purchase_date",
                "total_spent",
                "purchase_count",
            ]
        )

        was_first_purchase = not Transaction.objects.filter(customer=customer).exists()

        product_defaults = {
            "name": data["product_name"],
            "category": data["category"],
            "price": data["price"],
            "store_id": data["store_id"],
            "is_promotional": data["is_promotional"],
        }
        product, _ = Product.objects.get_or_create(
            product_code=data["product_code"], defaults=product_defaults
        )

        transaction = Transaction.objects.create(
            customer=customer,
            product=product,
            quantity=data["quantity"],
            total_amount=data["total"],
            bonus_earned=data["bonus_earned"],
            purchase_date=data["purchase_date"],
            purchase_time=data["purchase_time"],
            store_id=data["store_id"],
            is_promotional=data["is_promotional"],
        )

        response = {
            "msg": "Successfully",
            "transaction_id": transaction.id,
            "bonus_earned": float(transaction.bonus_earned or 0),
            "total_bonuses": float(customer.bonuses or 0),
            "is_first_purchase": was_first_purchase,
            "referrer": getattr(customer.referrer, "telegram_id", None),
        }
        return Response(response, status=status.HTTP_201_CREATED)


class SendMessageAPIView(APIView):
    """Minimal wrapper to send a Telegram message on behalf of the bot."""

    def post(self, request):
        telegram_id = request.data.get("telegram_id")
        text = request.data.get("text")

        if not telegram_id or not text:
            return Response(
                {"err": "telegram_id and text are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = CustomUser.objects.get(telegram_id=telegram_id)
        except CustomUser.DoesNotExist:
            return Response({"err": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if not config.BOT_TOKEN:
            logger.error("BOT_TOKEN is not configured; cannot send message")
            return Response(
                {"err": "Bot token is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        telegram_url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": user.telegram_id,
            "text": text,
            "parse_mode": "HTML",
        }

        try:
            response = requests.post(telegram_url, json=payload, timeout=5)
            response.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover - network failure
            logger.warning("Failed to send Telegram message: %s", exc)
            return Response(
                {"err": "Failed to send message to Telegram."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"msg": "Message sent successfully."})


@require_GET
@csrf_exempt
def healthz(_request):
    """Public health-check endpoint for container orchestration."""

    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_POST
@require_onec_auth
def onec_health(_request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_POST
@require_onec_auth
def onec_receipt(request):
    raw_body = request.body or b"{}"
    if isinstance(raw_body, (bytes, bytearray)):
        raw_body = raw_body.decode("utf-8")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid_json"}, status=400)

    serializer = ReceiptSerializer(data=payload)
    if not serializer.is_valid():
        return JsonResponse({"detail": serializer.errors}, status=400)
    data = serializer.validated_data

    idem_key = (
        getattr(request, "headers", {}).get("X-Idempotency-Key")
        or request.META.get("HTTP_X_IDEMPOTENCY_KEY")
    )
    if not idem_key:
        return JsonResponse({"detail": "missing idempotency key"}, status=400)

    if hasattr(Transaction, "idempotency_key") and Transaction.objects.filter(
        idempotency_key=idem_key
    ).exists():
        return JsonResponse(
            {"status": "already exists", "created_count": 0, "allocations": []},
            status=200,
        )

    dt_in = data["datetime"]
    dt_naive = dj_tz.make_naive(dt_in) if dj_tz.is_aware(dt_in) else dt_in
    purchase_date, purchase_time = dt_naive.date(), dt_naive.time()

    customer_block = data["customer"]
    telegram_id = customer_block.get("telegram_id")
    one_c_guid = customer_block.get("one_c_guid")

    user = None
    if one_c_guid:
        mapping = (
            OneCClientMap.objects.select_related("user")
            .filter(one_c_guid=one_c_guid)
            .first()
        )
        if mapping:
            user = mapping.user

    if not user and telegram_id:
        user = CustomUser.objects.filter(telegram_id=telegram_id).first()

    if not user:
        if telegram_id is None:
            return JsonResponse(
                {"detail": {"telegram_id": ["Обязательное поле для новых клиентов."]}},
                status=400,
            )
        user, _ = CustomUser.objects.get_or_create(telegram_id=telegram_id)

    if one_c_guid:
        OneCClientMap.objects.update_or_create(
            one_c_guid=one_c_guid, defaults={"user": user}
        )

    totals = data["totals"]
    total_amount = _as_decimal(totals["total_amount"])
    discount_total = _as_decimal(totals["discount_total"])
    bonus_spent = _as_decimal(totals["bonus_spent"])
    bonus_earned = _as_decimal(totals["bonus_earned"])

    positions = data["positions"]
    created_count = 0
    allocations: list[dict[str, Any]] = []
    denom = total_amount if total_amount > 0 else D("1")
    first_line = True

    with db_tx.atomic():
        for position in positions:
            code = position["product_code"]
            name = position.get("name") or "UNKNOWN"
            qty = _as_decimal(position["quantity"])
            price = _as_decimal(position["price"])
            discount_amount = _as_decimal(position.get("discount_amount", 0))
            is_promotional = bool(position.get("is_promotional", False))
            line_number = position["line_number"]

            pos_total = _quantize((price - discount_amount) * qty)
            pos_bonus_earned = _quantize(bonus_earned * (pos_total / denom))

            product_defaults = {
                "name": name,
                "price": price,
                "is_promotional": is_promotional,
            }
            if "category" in position:
                product_defaults["category"] = position["category"]
            if hasattr(Product, "store_id") and "store_id" in data:
                product_defaults.setdefault("store_id", data["store_id"])

            product, _ = Product.objects.get_or_create(
                product_code=code,
                defaults=product_defaults,
            )

            transaction_defaults = {
                "customer": user,
                "product": product,
                "quantity": qty,
                "total_amount": pos_total,
                "bonus_earned": pos_bonus_earned,
                "purchase_date": purchase_date,
                "purchase_time": purchase_time,
            }
            if hasattr(Transaction, "store_id") and "store_id" in data:
                transaction_defaults["store_id"] = data["store_id"]
            if hasattr(Transaction, "is_promotional"):
                transaction_defaults["is_promotional"] = is_promotional
            if hasattr(Transaction, "receipt_guid"):
                transaction_defaults["receipt_guid"] = data["receipt_guid"]
            if hasattr(Transaction, "receipt_line"):
                transaction_defaults["receipt_line"] = line_number
            if first_line and hasattr(Transaction, "idempotency_key"):
                transaction_defaults["idempotency_key"] = idem_key

            try:
                transaction, created = Transaction.objects.get_or_create(
                    receipt_guid=data["receipt_guid"],
                    receipt_line=line_number,
                    defaults=transaction_defaults,
                )
            except IntegrityError:
                logger.info("Receipt line already processed", extra={"line": line_number})
                created = False
            else:
                if created:
                    created_count += 1
                    allocations.append(
                        {
                            "product_code": code,
                            "quantity": float(qty),
                            "total_amount": float(pos_total),
                            "bonus_earned": float(pos_bonus_earned),
                        }
                    )
            finally:
                first_line = False

        if created_count > 0:
            user.total_spent = (user.total_spent or D("0")) + total_amount
            user.purchase_count = (user.purchase_count or 0) + 1
            user.last_purchase_date = dt_in if settings.USE_TZ else dt_naive
            user.bonuses = (user.bonuses or D("0")) - bonus_spent + bonus_earned
            user.save(
                update_fields=[
                    "total_spent",
                    "purchase_count",
                    "last_purchase_date",
                    "bonuses",
                ]
            )

    guid_for_resp = one_c_guid
    if not guid_for_resp:
        mapping = OneCClientMap.objects.filter(user=user).first()
        guid_for_resp = getattr(mapping, "one_c_guid", None)

    response = {
        "status": "ok" if created_count > 0 else "already exists",
        "receipt_guid": data["receipt_guid"],
        "created_count": created_count,
        "allocations": allocations,
        "customer": {
            "telegram_id": user.telegram_id,
            "one_c_guid": guid_for_resp,
            "bonus_balance": float(user.bonuses or D("0")),
            "total_spent": float(user.total_spent or D("0")),
            "purchase_count": user.purchase_count or 0,
            "last_purchase_date": (
                dt_in if settings.USE_TZ else dt_naive
            ).isoformat(),
        },
        "totals": {
            "total_amount": float(total_amount),
            "discount_total": float(discount_total),
            "bonus_spent": float(bonus_spent),
            "bonus_earned": float(bonus_earned),
        },
    }

    status_code = 201 if created_count > 0 else 200
    return JsonResponse(response, status=status_code)


@csrf_exempt
@require_POST
@require_onec_auth
def onec_customer_sync(request):
    raw = request.body or b""
    if not raw:
        return JsonResponse({"detail": "empty_body"}, status=400)
    try:
        payload_str = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw
        data = json.loads(payload_str)
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid_json"}, status=400)

    if "telegram_id" not in data:
        return JsonResponse({"detail": {"telegram_id": ["Обязательное поле."]}}, status=400)

    try:
        telegram_id = int(data["telegram_id"])
    except (TypeError, ValueError):
        return JsonResponse({"detail": {"telegram_id": ["Неверное значение"]}}, status=400)

    one_c_guid = str(data.get("one_c_guid") or "")
    bonus_balance = data.get("bonus_balance")
    referrer_tid = data.get("referrer_telegram_id")

    write_mode = any(
        [bonus_balance is not None, referrer_tid, one_c_guid]
    )

    user, _ = CustomUser.objects.get_or_create(telegram_id=telegram_id)

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
        except Exception:
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
        user.save()

    if one_c_guid:
        OneCClientMap.objects.update_or_create(
            one_c_guid=one_c_guid,
            defaults={"user": user},
        )

    mapping = OneCClientMap.objects.filter(user=user).first()
    guid_for_resp = getattr(mapping, "one_c_guid", None) or (one_c_guid or None)

    return JsonResponse(
        {
            "status": "ok" if write_mode else "lookup",
            "customer": {
                "telegram_id": user.telegram_id,
                "one_c_guid": guid_for_resp,
                "bonus_balance": float(user.bonuses or 0),
                "referrer_telegram_id": getattr(
                    getattr(user, "referrer", None), "telegram_id", None
                ),
            },
        }
    )


@csrf_exempt
@require_POST
@require_onec_auth
def onec_product_sync(request):
    raw_body = request.body or b"{}"
    if isinstance(raw_body, (bytes, bytearray)):
        raw_body = raw_body.decode("utf-8")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid_json"}, status=400)

    serializer = ProductUpdateSerializer(data=payload)
    if not serializer.is_valid():
        return JsonResponse({"detail": serializer.errors}, status=400)
    data = serializer.validated_data

    defaults = {
        "one_c_guid": data.get("one_c_guid"),
        "name": data["name"],
        "price": data["price"],
        "category": data["category"],
        "is_promotional": data["is_promotional"],
    }
    if hasattr(Product, "store_id"):
        defaults.setdefault("store_id", 0)

    product, created = Product.objects.update_or_create(
        product_code=data["product_code"], defaults=defaults
    )

    resp = {
        "status": "created" if created else "updated",
        "product": {
            "product_code": product.product_code,
            "one_c_guid": product.one_c_guid,
            "name": product.name,
            "price": float(product.price),
            "category": product.category,
            "is_promotional": product.is_promotional,
        },
    }
    return JsonResponse(resp, status=201 if created else 200)
