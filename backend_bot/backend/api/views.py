"""REST and webhook views exposed by the backend API."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal as D, ROUND_HALF_UP
from typing import Any

import requests
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction as db_tx
from django.db.models import F, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.utils import timezone as dj_tz
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from rest_framework import status
from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response
from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import filters

from main.models import CustomUser, Product, Transaction, Order
from src import config

from .models import OneCClientMap
from .security import require_onec_auth
from .serializers import (
    ProductUpdateSerializer,
    PurchaseSerializer,
    ReceiptSerializer,
    ProductListSerializer,
    OrderCreateSerializer,
    OrderListSerializer,
    CustomerProfileSerializer,
)

logger = logging.getLogger(__name__)


def _as_decimal(value: Any) -> D:
    if isinstance(value, D):
        return value
    return D(str(value))


def _quantize(amount: D) -> D:
    return amount.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def _onec_error(error_code: str, message: str, *, details: Any | None = None, status_code: int = 400):
    payload: dict[str, Any] = {"error_code": error_code, "message": message}
    if details is not None:
        payload["details"] = details
    return JsonResponse(payload, status=status_code)


def _find_first_error_code(errors: Any) -> str | None:
    if isinstance(errors, ErrorDetail):
        return str(errors.code)
    if isinstance(errors, (list, tuple, ReturnList)):
        for item in errors:
            code = _find_first_error_code(item)
            if code:
                return code
    if isinstance(errors, (dict, ReturnDict)):
        for item in errors.values():
            code = _find_first_error_code(item)
            if code:
                return code
    return None


class DuplicateReceiptLineError(Exception):
    def __init__(self, line_number: int):
        super().__init__(f"Duplicate receipt line {line_number}")
        self.line_number = line_number


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
    except json.JSONDecodeError as exc:
        logger.warning("onec_receipt: invalid JSON payload: %s", exc)
        return _onec_error(
            "invalid_json",
            "Request body must be valid JSON.",
            details={"error": str(exc)},
        )

    serializer = ReceiptSerializer(data=payload)
    if not serializer.is_valid():
        errors = serializer.errors
        error_code = _find_first_error_code(errors) or "invalid_payload"
        if error_code == "required":
            error_code = "missing_field"
        elif error_code in {"invalid", "null", "blank"}:
            error_code = "invalid_payload"
        message_map = {
            "missing_field": "Missing required field in payload.",
            "duplicate_receipt_line": "Receipt contains duplicate line_number entries.",
        }
        message = message_map.get(error_code, "Payload validation failed.")
        logger.warning(
            "onec_receipt: payload validation failed: code=%s details=%s",
            error_code,
            errors,
        )
        return _onec_error(error_code, message, details=errors)
    data = serializer.validated_data

    idem_key = (
        getattr(request, "headers", {}).get("X-Idempotency-Key")
        or request.META.get("HTTP_X_IDEMPOTENCY_KEY")
    )
    if not idem_key:
        return _onec_error(
            "missing_idempotency_key",
            "Header X-Idempotency-Key is required.",
        )

    existing_by_idem = False
    if hasattr(Transaction, "idempotency_key"):
        try:
            existing_by_idem = Transaction.objects.filter(
                idempotency_key=idem_key
            ).exists()
        except DjangoValidationError:
            return _onec_error(
                "invalid_idempotency_key",
                "Header X-Idempotency-Key must be a valid UUID.",
                details={"idempotency_key": idem_key},
            )
    if existing_by_idem:
        return JsonResponse(
            {"status": "already exists", "created_count": 0, "allocations": []},
            status=200,
        )

    dt_in = data["datetime"]
    dt_naive = dj_tz.make_naive(dt_in) if dj_tz.is_aware(dt_in) else dt_in
    purchase_date, purchase_time = dt_naive.date(), dt_naive.time()

    customer_block = data.get("customer") or {}
    telegram_id = customer_block.get("telegram_id")
    one_c_guid_raw = customer_block.get("one_c_guid")
    one_c_guid = (one_c_guid_raw or "").strip() or None

    user = None
    is_guest = False

    if one_c_guid:
        mapping = (
            OneCClientMap.objects.select_related("user")
            .filter(one_c_guid=one_c_guid)
            .first()
        )
        if not mapping:
            return _onec_error(
                "unknown_customer",
                "Customer GUID is not registered.",
                details={"one_c_guid": one_c_guid},
            )
        user = mapping.user

    if telegram_id is not None:
        user_by_tid = CustomUser.objects.filter(telegram_id=telegram_id).first()
        if not user_by_tid:
            return _onec_error(
                "unknown_customer",
                "Customer telegram_id is not registered.",
                details={"telegram_id": telegram_id},
            )
        if user and user_by_tid.id != user.id:
            return _onec_error(
                "conflicting_customer",
                "Customer identifiers refer to different users.",
                details={"telegram_id": telegram_id, "one_c_guid": one_c_guid},
            )
        user = user or user_by_tid

    if not user:
        if one_c_guid or telegram_id is not None:
            return _onec_error(
                "unknown_customer",
                "Customer identifiers are not registered.",
                details={"telegram_id": telegram_id, "one_c_guid": one_c_guid},
            )

        guest_tid = getattr(settings, "GUEST_TELEGRAM_ID", None)
        try:
            guest_tid_int = int(guest_tid)
        except (TypeError, ValueError):
            logger.error("Invalid GUEST_TELEGRAM_ID setting: %r", guest_tid)
            return _onec_error(
                "guest_user_not_configured",
                "Guest user is not configured on the server.",
                status_code=500,
            )

        user = CustomUser.objects.filter(telegram_id=guest_tid_int).first()
        if not user:
            logger.error(
                "Guest user with telegram_id %s not found", guest_tid_int
            )
            return _onec_error(
                "guest_user_not_found",
                "Guest user is missing in the database.",
                status_code=500,
                details={"telegram_id": guest_tid_int},
            )
        is_guest = True

    if one_c_guid:
        OneCClientMap.objects.update_or_create(
            one_c_guid=one_c_guid, defaults={"user": user}
        )

    totals = data["totals"]
    total_amount = _as_decimal(totals["total_amount"])
    discount_total = _as_decimal(totals["discount_total"])
    bonus_spent = _as_decimal(totals["bonus_spent"])
    bonus_earned = D("0") if is_guest else _as_decimal(totals["bonus_earned"])

    positions = data["positions"]

    pos_with, pos_without = [], []
    for position in positions:
        if "bonus_earned" in position and position["bonus_earned"] is not None:
            pos_with.append(position)
        else:
            pos_without.append(position)

    B_tot = _quantize(_as_decimal(totals.get("bonus_earned", "0")))
    B_fixed = _quantize(
        sum((_as_decimal(p["bonus_earned"]) for p in pos_with), D("0"))
    )
    B_left = B_tot - B_fixed
    if B_left < 0:
        logger.warning(
            "onec_receipt: positional bonuses exceed totals; clamping to totals"
        )
        B_left = D("0")

    if B_left > 0 and pos_without:
        totals_for_alloc: list[D] = []
        for p in pos_without:
            price = _as_decimal(p["price"])
            discount = _as_decimal(p.get("discount_amount", 0))
            qty = _as_decimal(p["quantity"])
            totals_for_alloc.append(_quantize((price - discount) * qty))
        denom_alloc = sum(totals_for_alloc) or D("1")

        allocated: list[D] = []
        running = D("0")
        for idx, p in enumerate(pos_without):
            if idx < len(pos_without) - 1:
                part = _quantize(B_left * (totals_for_alloc[idx] / denom_alloc))
                allocated.append(part)
                running += part
            else:
                allocated.append(_quantize(B_left - running))

        for p, val in zip(pos_without, allocated):
            p["bonus_earned"] = str(val)
    elif pos_without:
        for p in pos_without:
            p["bonus_earned"] = str(D("0"))

    if hasattr(Transaction, "receipt_guid") and hasattr(Transaction, "receipt_line"):
        existing_lines = set(
            Transaction.objects.filter(receipt_guid=data["receipt_guid"])
            .values_list("receipt_line", flat=True)
        )
    else:
        existing_lines = set()

    duplicate_lines = [
        pos["line_number"]
        for pos in positions
        if pos["line_number"] in existing_lines
    ]
    if duplicate_lines:
        logger.info(
            "onec_receipt: duplicate lines for receipt %s: %s",
            data["receipt_guid"],
            duplicate_lines,
        )
        return _onec_error(
            "duplicate_receipt_line",
            "Receipt line already processed.",
            details={
                "receipt_guid": data["receipt_guid"],
                "line_numbers": sorted(set(duplicate_lines)),
            },
        )

    created_count = 0
    allocations: list[dict[str, Any]] = []
    denom = total_amount if total_amount > 0 else D("1")
    first_line = True
    delta_bonus = D("0")
    total_spent_delta = D("0")
    purchase_increment = 1 if not existing_lines else 0
    purchased_at_value = dt_in if settings.USE_TZ else dt_naive

    try:
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
                pos_bonus_earned = _quantize(_as_decimal(position["bonus_earned"]))
                pos_bonus_spent = _quantize(bonus_spent * (pos_total / denom))

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
                if hasattr(Transaction, "purchased_at"):
                    transaction_defaults.setdefault("purchased_at", purchased_at_value)
                if hasattr(Transaction, "receipt_bonus_earned"):
                    transaction_defaults["receipt_bonus_earned"] = pos_bonus_earned
                if hasattr(Transaction, "receipt_bonus_spent"):
                    transaction_defaults["receipt_bonus_spent"] = pos_bonus_spent
                if first_line and hasattr(Transaction, "idempotency_key"):
                    transaction_defaults["idempotency_key"] = idem_key

                try:
                    transaction, created = Transaction.objects.get_or_create(
                        receipt_guid=data["receipt_guid"],
                        receipt_line=line_number,
                        defaults=transaction_defaults,
                    )
                except IntegrityError as exc:
                    logger.info(
                        "Receipt line already processed", extra={"line": line_number}
                    )
                    raise DuplicateReceiptLineError(line_number) from exc
                else:
                    if created:
                        created_count += 1
                        total_spent_delta += pos_total
                        delta_bonus += pos_bonus_earned - pos_bonus_spent
                        allocations.append(
                            {
                                "product_code": code,
                                "quantity": float(qty),
                                "total_amount": float(pos_total),
                                "bonus_earned": float(pos_bonus_earned),
                            }
                        )
                    else:
                        updates: dict[str, Any] = {}
                        if hasattr(Transaction, "receipt_bonus_earned") and getattr(
                            transaction, "receipt_bonus_earned", None
                        ) in (None,):
                            updates["receipt_bonus_earned"] = pos_bonus_earned
                        if getattr(transaction, "bonus_earned", None) != pos_bonus_earned:
                            updates["bonus_earned"] = pos_bonus_earned
                        if hasattr(Transaction, "receipt_bonus_spent") and getattr(
                            transaction, "receipt_bonus_spent", None
                        ) in (None,):
                            updates["receipt_bonus_spent"] = pos_bonus_spent
                        if hasattr(Transaction, "purchased_at") and getattr(
                            transaction, "purchased_at", None
                        ) is None:
                            updates["purchased_at"] = purchased_at_value
                        if updates:
                            Transaction.objects.filter(pk=transaction.pk).update(**updates)
                finally:
                    first_line = False
    except DuplicateReceiptLineError as exc:
        return _onec_error(
            "duplicate_receipt_line",
            "Receipt line already processed.",
            details={
                "receipt_guid": data["receipt_guid"],
                "line_numbers": [exc.line_number],
            },
        )

    if created_count > 0 and not is_guest:
        bonus_delta_to_apply = _quantize(delta_bonus)
        total_spent_delta = _quantize(total_spent_delta)
        update_kwargs: dict[str, Any] = {
            "bonuses": Coalesce(F("bonuses"), Value(D("0"))) + bonus_delta_to_apply,
            "last_purchase_date": purchased_at_value,
            "total_spent": Coalesce(F("total_spent"), Value(D("0")))
            + total_spent_delta,
        }
        if purchase_increment > 0:
            update_kwargs["purchase_count"] = (
                Coalesce(F("purchase_count"), Value(0)) + purchase_increment
            )

        CustomUser.objects.filter(id=user.id).update(**update_kwargs)
        user.refresh_from_db(
            fields=["bonuses", "purchase_count", "total_spent", "last_purchase_date"]
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
            "id": user.id,  # <--- ВОТ ТУТ НОВАЯ СТРОЧКА!
            "one_c_guid": guid_for_resp,
            "qr_code": user.qr_code,
            "bonus_balance": float(user.bonuses or D("0")),
            "referrer_telegram_id": getattr(
                getattr(user, "referrer", None), "telegram_id", None
            ),
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

    telegram_raw = data.get("telegram_id")
    qr_code = str(data.get("qr_code") or "").strip()

    telegram_id: int | None
    if telegram_raw in (None, "", False):
        telegram_id = None
    else:
        try:
            telegram_id = int(telegram_raw)
        except (TypeError, ValueError):
            return JsonResponse({"detail": {"telegram_id": ["Неверное значение"]}}, status=400)

    if telegram_id is None and not qr_code:
        return JsonResponse(
            {"detail": {"telegram_id": ["Нужно указать telegram_id или qr_code."]}},
            status=400,
        )

    user: CustomUser | None = None
    if qr_code:
        user = CustomUser.objects.filter(qr_code=qr_code).first()
        if not user:
            return JsonResponse(
                {"detail": {"qr_code": ["Пользователь не найден"]}},
                status=404,
            )

    if telegram_id is not None:
        if user and user.telegram_id != telegram_id:
            return JsonResponse(
                {"detail": {"telegram_id": ["Не совпадает с QR-кодом"]}},
                status=400,
            )

        user_by_tid = CustomUser.objects.filter(telegram_id=telegram_id).first()
        if not user_by_tid:
            return JsonResponse(
                {"detail": {"telegram_id": ["Пользователь не найден"]}},
                status=404,
            )
        if user and user_by_tid.id != user.id:
            return JsonResponse(
                {"detail": {"telegram_id": ["Не совпадает с QR-кодом"]}},
                status=400,
            )
        user = user or user_by_tid

    if not user:
        return JsonResponse(
            {"detail": {"qr_code": ["Пользователь не найден"]}},
            status=404,
        )

    if telegram_id is not None and user.telegram_id != telegram_id:
        return JsonResponse(
            {"detail": {"telegram_id": ["Не совпадает с QR-кодом"]}},
            status=400,
        )

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
                "id": user.id,  # <--- ВОТ ТУТ НОВАЯ СТРОЧКА!
                "one_c_guid": guid_for_resp,
                "qr_code": user.qr_code,
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

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True) 
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]

    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']


class OrderCreateView(generics.CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer
    permission_classes = [AllowAny]


class OrderListUserView(generics.ListAPIView):
    serializer_class = OrderListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')
        
        if user_id:
            return Order.objects.filter(customer_id=user_id).order_by('-created_at')
        
        return Order.objects.none()
    

class OrderDetailView(generics.RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderListSerializer
    permission_classes = [AllowAny]


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """
    Получение и обновление профиля клиента.
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomerProfileSerializer
    permission_classes = [AllowAny]

    parser_classes = [MultiPartParser, FormParser, JSONParser]