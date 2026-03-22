from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from decimal import Decimal as D

from django.conf import settings
from django.db.models import F, Max, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone as dj_tz
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import CustomerPermission
from apps.loyalty.models import CustomUser, Product, Transaction

from apps.api.security import require_onec_auth
from apps.loyalty.serializers import BonusHistorySerializer, PurchaseSerializer

PAGE_SIZE = 20


def _encode_cursor(sort_date, receipt_guid: str) -> str:
    """Encode (sort_date, receipt_guid) pair into an opaque cursor string."""
    payload = {
        "d": sort_date.isoformat() if sort_date else "",
        "g": receipt_guid,
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    """Decode cursor string back into (sort_date, receipt_guid).

    Raises ValueError on any decoding problem.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode())
        payload = json.loads(raw)
        sort_date = datetime.fromisoformat(payload["d"])
        receipt_guid = payload["g"]
    except Exception as exc:
        raise ValueError(f"Invalid cursor: {exc}") from exc
    return sort_date, receipt_guid


class BonusHistoryView(GenericAPIView):
    """Customer bonus/purchase history with cursor-based pagination."""

    permission_classes = [CustomerPermission]
    serializer_class = BonusHistorySerializer

    def get(self, request):
        user = request.telegram_user

        qs = (
            Transaction.objects.filter(
                customer=user,
                receipt_guid__isnull=False,
            )
            .exclude(receipt_guid__exact="")
            .values("receipt_guid")
            .annotate(
                sort_date=Max("purchased_at"),
                purchase_total=Coalesce(Sum("total_amount"), D("0")),
                bonus_earned=Coalesce(Sum("receipt_bonus_earned"), D("0")),
                bonus_spent=Coalesce(Sum("receipt_bonus_spent"), D("0")),
            )
        )

        cursor_param = request.query_params.get("cursor")
        if cursor_param:
            try:
                cursor_date, cursor_guid = _decode_cursor(cursor_param)
            except ValueError as exc:
                return Response(
                    {"error": str(exc)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qs = qs.filter(
                Q(sort_date__lt=cursor_date)
                | Q(sort_date=cursor_date, receipt_guid__lt=cursor_guid)
            )

        qs = qs.order_by("-sort_date", "-receipt_guid")
        rows = list(qs[: PAGE_SIZE + 1])

        if len(rows) > PAGE_SIZE:
            results = rows[:PAGE_SIZE]
            last = results[-1]
            next_cursor = _encode_cursor(last["sort_date"], last["receipt_guid"])
        else:
            results = rows
            next_cursor = None

        serializer = self.get_serializer(results, many=True)
        return Response({"next_cursor": next_cursor, "results": serializer.data})


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

        CustomUser.objects.filter(pk=customer.pk).update(
            bonuses=data["total_bonuses"],
            last_purchase_date=purchase_dt,
            total_spent=Coalesce(F("total_spent"), D("0")) + data["total"],
            purchase_count=Coalesce(F("purchase_count"), 0) + 1,
        )
        customer.refresh_from_db()

        was_first_purchase = not Transaction.objects.filter(customer=customer).exists()

        product_defaults = {
            "name": data["product_name"],
            "category_text": data["category"],
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
