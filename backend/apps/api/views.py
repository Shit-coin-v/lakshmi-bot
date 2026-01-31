from __future__ import annotations

import logging
import requests
from datetime import datetime, timezone
from decimal import Decimal as D

from django.conf import settings
from django.utils import timezone as dj_tz
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status, generics
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.main.models import CustomUser, Product, Transaction, Order

from .security import require_onec_auth
from .serializers import (
    CustomerProfileSerializer,
    OrderListSerializer,
    PurchaseSerializer,
)
from apps.orders.views import OrderCreateView  # noqa: F401
from apps.orders.views import OrderDetailView  # noqa: F401
from apps.orders.views import ProductListView  # noqa: F401
from apps.notifications.views import NotificationViewSet  # noqa: F401
from apps.notifications.views import PushRegisterView  # noqa: F401
from apps.notifications.views import UpdateFCMTokenView  # noqa: F401

logger = logging.getLogger(__name__)


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

        if not settings.BOT_TOKEN:
            logger.error("BOT_TOKEN is not configured; cannot send message")
            return Response(
                {"err": "Bot token is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        telegram_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": user.telegram_id,
            "text": text,
            "parse_mode": "HTML",
        }

        try:
            response = requests.post(telegram_url, json=payload, timeout=5)
            response.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover
            logger.warning("Failed to send Telegram message: %s", exc)
            return Response(
                {"err": "Failed to send message to Telegram."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"msg": "Message sent successfully."}, status=status.HTTP_200_OK)


class OrderListUserView(generics.ListAPIView):
    serializer_class = OrderListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")

        if user_id:
            return Order.objects.filter(customer_id=user_id).order_by("-created_at")

        return Order.objects.none()


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """Получение и обновление профиля клиента."""

    queryset = CustomUser.objects.all()
    serializer_class = CustomerProfileSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
