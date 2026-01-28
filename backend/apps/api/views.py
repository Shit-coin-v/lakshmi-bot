from __future__ import annotations

import logging
import requests
from datetime import datetime, timezone
from decimal import Decimal as D

from django.conf import settings
from django.utils import timezone as dj_tz
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status, generics, filters, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action

from apps.common.health import healthz  # noqa: F401
from apps.integrations.onec.customer_sync import onec_customer_sync  # noqa: F401
from apps.integrations.onec.health import onec_health  # noqa: F401
from apps.integrations.onec.order_create import onec_order_create  # noqa: F401
from apps.integrations.onec.order_status import onec_order_status  # noqa: F401
from apps.integrations.onec.orders_pending import onec_orders_pending  # noqa: F401
from apps.integrations.onec.product_sync_endpoint import onec_product_sync  # noqa: F401
from apps.integrations.onec.receipt import onec_receipt  # noqa: F401
from apps.main.models import (
    CustomUser, Product, Transaction, Order, 
    CustomerDevice, Notification, NotificationOpenEvent
    )

from .permissions import ApiKeyPermission
from .security import require_onec_auth
from .serializers import (
    CustomerProfileSerializer,
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    ProductListSerializer,
    PurchaseSerializer,
    NotificationSerializer,
    NotificationReadSerializer,
    UpdateFCMTokenSerializer,

)

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


class PushRegisterView(APIView):
    # ApiKeyPermission у тебя уже завязан на X-Api-Key 👍
    permission_classes = []  # НЕ ставим DRF-auth; проверка только через ApiKeyPermission ниже
    authentication_classes = []

    def post(self, request):
        # ручная проверка через permission класс
        perm = ApiKeyPermission()
        if not perm.has_permission(request, self):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        fcm_token = (request.data.get("fcm_token") or "").strip()
        platform = (request.data.get("platform") or "android").lower()
        customer_id = request.data.get("customer_id")

        if not fcm_token or not customer_id:
            return Response(
                {"detail": "customer_id and fcm_token are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            customer = CustomUser.objects.get(id=int(customer_id))
        except (TypeError, ValueError, CustomUser.DoesNotExist):
            return Response({"detail": "customer not found"}, status=status.HTTP_404_NOT_FOUND)

        device, created = CustomerDevice.objects.update_or_create(
            fcm_token=fcm_token,
            defaults={"customer": customer, "platform": platform},
        )

        logger.info(
            "Registered FCM token for customer=%s | platform=%s | created=%s",
            customer.id,
            platform,
            created,
        )

        return Response({"status": "ok", "device_id": device.id}, status=status.HTTP_200_OK)
    

class UpdateFCMTokenView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        perm = ApiKeyPermission()
        if not perm.has_permission(request, self):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        s = UpdateFCMTokenSerializer(data=request.data)
        if not s.is_valid():
            return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

        customer_id = int(s.validated_data["customer_id"])
        fcm_token = s.validated_data["fcm_token"].strip()
        platform = s.validated_data.get("platform", "android")

        try:
            customer = CustomUser.objects.get(id=customer_id)
        except CustomUser.DoesNotExist:
            return Response({"detail": "customer not found"}, status=status.HTTP_404_NOT_FOUND)

        device, created = CustomerDevice.objects.update_or_create(
            fcm_token=fcm_token,
            defaults={"customer": customer, "platform": platform},
        )

        return Response(
            {"status": "ok", "device_id": device.id, "created": created},
            status=status.HTTP_200_OK,
        )



class OrderDetailView(generics.RetrieveAPIView):
    queryset = Order.objects.all().prefetch_related("items__product")
    serializer_class = OrderDetailSerializer
    permission_classes = [AllowAny]


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]

    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]


class OrderCreateView(generics.CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer
    permission_classes = [AllowAny]


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


class NotificationViewSet(viewsets.ViewSet):
    permission_classes = []
    authentication_classes = []

    def _check_api_key(self, request):
        perm = ApiKeyPermission()
        if not perm.has_permission(request, self):
            raise PermissionDenied("Forbidden")

    def list(self, request):
        self._check_api_key(request)

        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response([], status=200)

        qs = (
            Notification.objects
            .filter(user_id=int(user_id))
            .order_by("-created_at")
        )
        return Response(NotificationSerializer(qs, many=True).data, status=200)

    def retrieve(self, request, pk=None):
        self._check_api_key(request)

        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"detail": "user_id is required"}, status=400)

        try:
            n = Notification.objects.get(pk=int(pk), user_id=int(user_id))
        except Notification.DoesNotExist:
            return Response({"detail": "not found"}, status=404)

        return Response(NotificationSerializer(n).data, status=200)
    
    def read(self, request, pk=None):
        perm = ApiKeyPermission()
        if not perm.has_permission(request, self):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get("user_id") or request.query_params.get("user_id")
        if not user_id:
            return Response({"detail": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            notif = Notification.objects.select_related("user").get(
                pk=int(pk),
                user_id=int(user_id),
            )
        except (TypeError, ValueError):
            return Response({"detail": "invalid id"}, status=status.HTTP_400_BAD_REQUEST)
        except Notification.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        if not notif.is_read:
            notif.is_read = True
            notif.save(update_fields=["is_read"])

        try:
            source = (request.data.get("source") or request.query_params.get("source") or "inapp")
            if source not in {"inapp", "push"}:
                source = "inapp"

            NotificationOpenEvent.objects.get_or_create(
                notification=notif,
                user=notif.user,
                defaults={"source": source},
            )
        except Exception:
            logger.exception("Failed to log notification open event notification_id=%s", notif.id)

        return Response({"status": "ok", "id": notif.id, "is_read": True}, status=status.HTTP_200_OK)



    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        self._check_api_key(request)

        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"unread_count": 0}, status=200)

        cnt = Notification.objects.filter(user_id=int(user_id), is_read=False).count()
        return Response({"unread_count": cnt}, status=200)

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        self._check_api_key(request)

        s = NotificationReadSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        user_id = int(s.validated_data["user_id"])
        source = s.validated_data.get("source") or "inapp"

        try:
            n = Notification.objects.get(pk=int(pk), user_id=user_id)
        except Notification.DoesNotExist:
            return Response({"detail": "not found"}, status=404)

        NotificationOpenEvent.objects.get_or_create(
            notification=n,
            defaults={"user_id": user_id, "source": source},
        )

        if not n.is_read:
            n.is_read = True
            n.save(update_fields=["is_read"])

        cnt = Notification.objects.filter(user_id=user_id, is_read=False).count()
        return Response({"status": "ok", "unread_count": cnt}, status=200)
