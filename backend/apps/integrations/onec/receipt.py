from __future__ import annotations

import json
import logging
from decimal import Decimal as D, ROUND_HALF_UP
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction as db_tx
from django.db.models import F, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.utils import timezone as dj_tz
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.api.security import require_onec_auth
from apps.integrations.onec.utils import onec_error

logger = logging.getLogger(__name__)


def _as_decimal(value: Any) -> D:
    if isinstance(value, D):
        return value
    return D(str(value))


def _quantize(amount: D) -> D:
    return amount.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def _find_first_error_code(errors: Any) -> str | None:
    from rest_framework.exceptions import ErrorDetail
    from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList

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


def _try_referral_reward(referee, receipt_guid: str):
    """Начислить 50 бонусов реферу за первую покупку реферала. Idempotent, fail-open."""
    from apps.loyalty.models import ReferralReward
    from apps.integrations.onec.tasks import send_referral_reward_to_onec

    referrer = referee.referrer
    if not referrer or not referrer.card_id:
        return

    reward, created = ReferralReward.objects.get_or_create(
        referee=referee,
        defaults={
            "referrer": referrer,
            "bonus_amount": D("50"),
            "receipt_guid": receipt_guid,
            "source": "telegram" if referee.auth_method == "telegram" else "app",
            "status": ReferralReward.Status.PENDING,
        },
    )
    if not created:
        return  # уже начислено ранее

    db_tx.on_commit(
        lambda rid=reward.id: send_referral_reward_to_onec.delay(rid)
    )


@csrf_exempt
@require_POST
@require_onec_auth
def onec_receipt(request):
    from apps.api.models import OneCClientMap
    from apps.integrations.onec.serializers import ReceiptSerializer
    from apps.loyalty.models import CustomUser, Product, Transaction

    raw_body = request.body or b"{}"
    if isinstance(raw_body, (bytes, bytearray)):
        raw_body = raw_body.decode("utf-8")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        logger.warning("onec_receipt: invalid JSON payload: %s", exc)
        return onec_error(
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
        return onec_error(error_code, message, details=errors)
    data = serializer.validated_data

    idem_key = (
        getattr(request, "headers", {}).get("X-Idempotency-Key")
        or request.META.get("HTTP_X_IDEMPOTENCY_KEY")
    )
    if not idem_key:
        return onec_error(
            "missing_idempotency_key",
            "Header X-Idempotency-Key is required.",
        )

    existing_by_idem = False
    if hasattr(Transaction, "idempotency_key"):
        try:
            existing_by_idem = Transaction.objects.filter(idempotency_key=idem_key).exists()
        except DjangoValidationError:
            return onec_error(
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
    card_id = (customer_block.get("card_id") or "").strip() or None

    user = None
    is_guest = False

    if card_id:
        user = CustomUser.objects.select_related("referrer").filter(card_id=card_id).first()
        if not user:
            return onec_error(
                "unknown_customer",
                "Customer card_id is not registered.",
                details={"card_id": card_id},
            )
    else:
        guest_tid = getattr(settings, "GUEST_TELEGRAM_ID", None)
        try:
            guest_tid_int = int(guest_tid)
        except (TypeError, ValueError):
            logger.error("Invalid GUEST_TELEGRAM_ID setting: %r", guest_tid)
            return onec_error(
                "guest_user_not_configured",
                "Guest user is not configured on the server.",
                status_code=500,
            )

        user = CustomUser.objects.filter(telegram_id=guest_tid_int).first()
        if not user:
            logger.error("Guest user with telegram_id %s not found", guest_tid_int)
            return onec_error(
                "guest_user_not_found",
                "Guest user is missing in the database.",
                status_code=500,
                details={"telegram_id": guest_tid_int},
            )
        is_guest = True

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
    B_fixed = _quantize(sum((_as_decimal(p["bonus_earned"]) for p in pos_with), D("0")))
    B_left = B_tot - B_fixed
    if B_left < 0:
        logger.warning("onec_receipt: positional bonuses exceed totals; clamping to totals")
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
        for idx, _p in enumerate(pos_without):
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
        return onec_error(
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

                product_defaults = {"name": name, "price": price, "is_promotional": is_promotional}
                if "category" in position:
                    product_defaults["category_text"] = position["category"]
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
                if hasattr(Transaction, "purchase_type"):
                    transaction_defaults["purchase_type"] = data.get("purchase_type", "in_store")
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
                    logger.info("Receipt line already processed", extra={"line": line_number})
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
        return onec_error(
            "duplicate_receipt_line",
            "Receipt line already processed.",
            details={"receipt_guid": data["receipt_guid"], "line_numbers": [exc.line_number]},
        )

    if created_count > 0 and not is_guest:
        bonus_delta_to_apply = _quantize(delta_bonus)
        # Если все позиции чека созданы — берём total_amount из 1С (источник истины).
        # Если только часть (partial delivery) — используем сумму по позициям.
        if created_count == len(positions):
            total_spent_delta = _quantize(total_amount)
        else:
            total_spent_delta = _quantize(total_spent_delta)
        update_kwargs: dict[str, Any] = {
            "bonuses": Coalesce(F("bonuses"), Value(D("0"))) + bonus_delta_to_apply,
            "last_purchase_date": purchased_at_value,
            "total_spent": Coalesce(F("total_spent"), Value(D("0"))) + total_spent_delta,
        }
        if purchase_increment > 0:
            update_kwargs["purchase_count"] = Coalesce(F("purchase_count"), Value(0)) + purchase_increment

        CustomUser.objects.filter(id=user.id).update(**update_kwargs)
        user.refresh_from_db(fields=["bonuses", "purchase_count", "total_spent", "last_purchase_date"])

    # --- Campaign reward check (fail-open, async via Celery) ---
    if not is_guest and user.card_id:
        try:
            from apps.campaigns.services import evaluate_campaign_reward
            from apps.campaigns.models import CampaignRewardLog

            reward = evaluate_campaign_reward(
                customer=user,
                total_amount=total_amount,
                positions=positions,
                receipt_guid=data["receipt_guid"],
            )
            if reward:
                log, _created = CampaignRewardLog.objects.get_or_create(
                    receipt_guid=data["receipt_guid"],
                    defaults={
                        "customer": user,
                        "assignment_id": reward.assignment_id,
                        "campaign_id": reward.campaign_id,
                        "rule_id": reward.rule_id,
                        "reward_type": reward.reward_type,
                        "bonus_amount": reward.bonus_amount,
                        "is_accrual": reward.is_accrual,
                        "status": CampaignRewardLog.Status.PENDING,
                    },
                )
                if log.status != CampaignRewardLog.Status.SUCCESS:
                    from apps.integrations.onec.tasks import send_campaign_reward_to_onec
                    from django.db import transaction as db_tx_hook
                    db_tx_hook.on_commit(
                        lambda lid=log.id: send_campaign_reward_to_onec.delay(lid)
                    )
        except Exception:
            logger.exception(
                "campaign_reward: failed user=%d receipt=%s",
                user.id, data["receipt_guid"],
            )

    # --- Referral reward check (one-time, idempotent) ---
    if not is_guest and created_count > 0 and user.referrer_id:
        try:
            _try_referral_reward(user, receipt_guid=data["receipt_guid"])
        except Exception:
            logger.exception(
                "referral_reward: failed user=%d receipt=%s",
                user.id, data["receipt_guid"],
            )

    mapping = OneCClientMap.objects.filter(user=user).first()
    guid_for_resp = getattr(mapping, "one_c_guid", None)

    response = {
        "status": "ok" if created_count > 0 else "already exists",
        "receipt_guid": data["receipt_guid"],
        "created_count": created_count,
        "allocations": allocations,
        "customer": {
            "telegram_id": user.telegram_id,
            "id": user.id,
            "card_id": user.card_id,
            "one_c_guid": guid_for_resp,
            "qr_code": user.qr_code,
            "bonus_balance": float(user.bonuses or D("0")),
            "referrer_telegram_id": getattr(getattr(user, "referrer", None), "telegram_id", None),
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
