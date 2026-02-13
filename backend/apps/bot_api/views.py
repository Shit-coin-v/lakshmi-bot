import logging
from datetime import date

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.models import OneCClientMap
from apps.common.permissions import ApiKeyPermission
from apps.main.models import (
    CustomUser,
    NewsletterDelivery,
    NewsletterOpenEvent,
)
from apps.notifications.models import CourierNotificationMessage
from apps.orders.models import Order

from .serializers import (
    ActiveOrderSerializer,
    BotActivityCreateSerializer,
    BotOrderDetailSerializer,
    BotUserSerializer,
    CourierMessageBulkDeleteSerializer,
    CourierMessageSerializer,
    NewsletterOpenResponseSerializer,
    NewsletterOpenSerializer,
    OneCMapUpsertSerializer,
    UserPatchSerializer,
    UserRegisterSerializer,
)

logger = logging.getLogger(__name__)


# --- Customer Bot views ---


class UserByTelegramIdView(APIView):
    """GET /api/bot/users/by-telegram-id/<telegram_id>/"""

    permission_classes = [ApiKeyPermission]

    def get(self, request, telegram_id):
        try:
            user = CustomUser.objects.get(telegram_id=telegram_id)
        except CustomUser.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BotUserSerializer(user).data)


class UserRegisterView(generics.CreateAPIView):
    """POST /api/bot/users/register/"""

    permission_classes = [ApiKeyPermission]
    serializer_class = UserRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(BotUserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserPatchView(APIView):
    """PATCH /api/bot/users/<pk>/"""

    permission_classes = [ApiKeyPermission]

    def patch(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserPatchSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(BotUserSerializer(user).data)


class BotActivityCreateView(generics.CreateAPIView):
    """POST /api/bot/activities/"""

    permission_classes = [ApiKeyPermission]
    serializer_class = BotActivityCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activity = serializer.save()
        return Response(
            {"id": activity.id, "action": activity.action},
            status=status.HTTP_201_CREATED,
        )


class NewsletterOpenView(APIView):
    """POST /api/bot/newsletter/open/

    Atomic: find delivery by token, set opened_at, create open event.
    Idempotent: double-open returns the same delivery without error.
    """

    permission_classes = [ApiKeyPermission]

    def post(self, request):
        serializer = NewsletterOpenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        telegram_user_id = serializer.validated_data["telegram_user_id"]
        raw_data = serializer.validated_data.get("raw_callback_data", "")

        try:
            with transaction.atomic():
                delivery = (
                    NewsletterDelivery.objects.select_for_update()
                    .select_related("message")
                    .filter(open_token=token)
                    .first()
                )
                if not delivery:
                    return Response(
                        {"detail": "Delivery not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                newly_opened = False
                if delivery.opened_at is None:
                    delivery.opened_at = timezone.now()
                    delivery.save(update_fields=["opened_at", "updated_at"])
                    NewsletterOpenEvent.objects.create(
                        delivery=delivery,
                        raw_callback_data=(raw_data or "")[:128],
                        telegram_user_id=telegram_user_id,
                    )
                    newly_opened = True
        except IntegrityError:
            # Race condition: another request already created the event
            delivery = (
                NewsletterDelivery.objects.select_related("message")
                .filter(open_token=token)
                .first()
            )
            if not delivery:
                return Response(
                    {"detail": "Delivery not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            newly_opened = False

        return Response(
            NewsletterOpenResponseSerializer(
                {
                    "delivery_id": delivery.id,
                    "newly_opened": newly_opened,
                    "message_text": delivery.message.message_text,
                }
            ).data
        )


class OneCMapUpsertView(APIView):
    """POST /api/bot/onec-map/upsert/

    Upsert OneCClientMap: if user_id already has a mapping, update guid.
    """

    permission_classes = [ApiKeyPermission]

    def post(self, request):
        serializer = OneCMapUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]
        one_c_guid = serializer.validated_data["one_c_guid"]

        if not CustomUser.objects.filter(pk=user_id).exists():
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        mapping, created = OneCClientMap.objects.update_or_create(
            user_id=user_id,
            defaults={"one_c_guid": one_c_guid},
        )
        return Response(
            {
                "id": mapping.id,
                "user_id": mapping.user_id,
                "one_c_guid": mapping.one_c_guid,
                "created": created,
            },
            status=status.HTTP_200_OK,
        )


# --- Courier Bot views ---


class ActiveOrdersView(generics.ListAPIView):
    """GET /api/bot/orders/active/"""

    permission_classes = [ApiKeyPermission]
    serializer_class = ActiveOrderSerializer

    def get_queryset(self):
        return Order.objects.filter(
            status__in=("ready", "delivery", "arrived")
        ).order_by("created_at")


class BotOrderDetailView(APIView):
    """GET /api/bot/orders/<pk>/detail/"""

    permission_classes = [ApiKeyPermission]

    def get(self, request, pk):
        try:
            order = (
                Order.objects.select_related("customer")
                .prefetch_related("items__product")
                .get(pk=pk)
            )
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BotOrderDetailSerializer(order).data)


class CompletedTodayView(APIView):
    """GET /api/bot/orders/completed-today/?courier_tg_id=<int>"""

    permission_classes = [ApiKeyPermission]

    def get(self, request):
        courier_tg_id = request.query_params.get("courier_tg_id")
        if not courier_tg_id:
            return Response(
                {"detail": "courier_tg_id query param is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            courier_tg_id = int(courier_tg_id)
        except (ValueError, TypeError):
            return Response(
                {"detail": "courier_tg_id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = date.today()
        count = Order.objects.filter(
            status="completed",
            delivered_by=courier_tg_id,
            completed_at__date=today,
        ).count()

        return Response({"count": count, "total": count * 150})


class CourierMessageListView(generics.ListAPIView):
    """GET /api/bot/courier-messages/?courier_tg_id=<int>"""

    permission_classes = [ApiKeyPermission]
    serializer_class = CourierMessageSerializer

    def get_queryset(self):
        courier_tg_id = self.request.query_params.get("courier_tg_id")
        if not courier_tg_id:
            return CourierNotificationMessage.objects.none()
        return CourierNotificationMessage.objects.filter(courier_tg_id=courier_tg_id).order_by("id")


class CourierMessageDeleteView(APIView):
    """DELETE /api/bot/courier-messages/<pk>/"""

    permission_classes = [ApiKeyPermission]

    def delete(self, request, pk):
        deleted, _ = CourierNotificationMessage.objects.filter(pk=pk).delete()
        if not deleted:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourierMessageBulkDeleteView(APIView):
    """POST /api/bot/courier-messages/bulk-delete/"""

    permission_classes = [ApiKeyPermission]

    def post(self, request):
        serializer = CourierMessageBulkDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]
        deleted, _ = CourierNotificationMessage.objects.filter(pk__in=ids).delete()
        return Response({"deleted": deleted})
