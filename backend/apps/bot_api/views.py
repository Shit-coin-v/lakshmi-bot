import logging
from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Q
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
from apps.notifications.models import CourierNotificationMessage, PickerNotificationMessage
from apps.orders.models import CourierProfile, Order, PickerProfile

from .serializers import (
    ActiveOrderSerializer,
    BotActivityCreateSerializer,
    BotOrderDetailSerializer,
    BotUserSerializer,
    CourierMessageBulkDeleteSerializer,
    CourierMessageSerializer,
    CourierProfileSerializer,
    CourierToggleAcceptingSerializer,
    NewsletterOpenResponseSerializer,
    NewsletterOpenSerializer,
    OneCMapUpsertSerializer,
    PickerMessageBulkDeleteSerializer,
    PickerMessageSerializer,
    StaffRegisterSerializer,
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
    """GET /api/bot/orders/active/?courier_tg_id=<int>

    If courier_tg_id is provided, returns only orders assigned to that courier.
    Otherwise returns all active orders (backward compat).
    """

    permission_classes = [ApiKeyPermission]
    serializer_class = ActiveOrderSerializer

    def get_queryset(self):
        qs = Order.objects.filter(
            status__in=("ready", "delivery", "arrived")
        ).order_by("created_at")
        courier_tg_id = self.request.query_params.get("courier_tg_id")
        if courier_tg_id:
            try:
                qs = qs.filter(delivered_by=int(courier_tg_id))
            except (ValueError, TypeError):
                return Order.objects.none()
        return qs


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

        from django.db.models import Sum

        today = date.today()
        qs = Order.objects.filter(
            status="completed",
            delivered_by=courier_tg_id,
            completed_at__date=today,
        )
        count = qs.count()
        total = qs.aggregate(total=Sum("delivery_price"))["total"] or Decimal("0")

        return Response({"count": count, "total": f"{total:.2f}"})


# --- Picker Bot views ---


class NewOrdersView(generics.ListAPIView):
    """GET /api/bot/orders/new/"""

    permission_classes = [ApiKeyPermission]
    serializer_class = ActiveOrderSerializer

    def get_queryset(self):
        return Order.objects.filter(status="new").order_by("created_at")


class PickerActiveOrdersView(generics.ListAPIView):
    """GET /api/bot/orders/my-active/?assembler_tg_id=<int>

    Orders assigned to picker: accepted, assembly, or ready+pickup.
    """

    permission_classes = [ApiKeyPermission]
    serializer_class = ActiveOrderSerializer

    def get_queryset(self):
        assembler_tg_id = self.request.query_params.get("assembler_tg_id")
        if not assembler_tg_id:
            return Order.objects.none()
        try:
            tg_id = int(assembler_tg_id)
        except (ValueError, TypeError):
            return Order.objects.none()
        return Order.objects.filter(
            Q(assembled_by=tg_id, status__in=("accepted", "assembly"))
            | Q(assembled_by=tg_id, status="ready", fulfillment_type="pickup")
        ).order_by("created_at")


class AssembledTodayView(APIView):
    """GET /api/bot/orders/assembled-today/?assembler_tg_id=<int>"""

    permission_classes = [ApiKeyPermission]

    def get(self, request):
        assembler_tg_id = request.query_params.get("assembler_tg_id")
        if not assembler_tg_id:
            return Response(
                {"detail": "assembler_tg_id query param is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            assembler_tg_id = int(assembler_tg_id)
        except (ValueError, TypeError):
            return Response(
                {"detail": "assembler_tg_id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = date.today()
        count = Order.objects.filter(
            assembled_by=assembler_tg_id,
            status__in=("ready", "completed"),
            created_at__date=today,
        ).count()

        return Response({"count": count})


class PickerMessageListView(generics.ListAPIView):
    """GET /api/bot/picker-messages/?picker_tg_id=<int>"""

    permission_classes = [ApiKeyPermission]
    serializer_class = PickerMessageSerializer

    def get_queryset(self):
        picker_tg_id = self.request.query_params.get("picker_tg_id")
        if not picker_tg_id:
            return PickerNotificationMessage.objects.none()
        return PickerNotificationMessage.objects.filter(picker_tg_id=picker_tg_id).order_by("id")


class PickerMessageBulkDeleteView(APIView):
    """POST /api/bot/picker-messages/bulk-delete/"""

    permission_classes = [ApiKeyPermission]

    def post(self, request):
        serializer = PickerMessageBulkDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]
        deleted, _ = PickerNotificationMessage.objects.filter(pk__in=ids).delete()
        return Response({"deleted": deleted})


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


class CourierProfileView(APIView):
    """GET /api/bot/courier/profile/?courier_tg_id=<int>"""

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

        profile, _ = CourierProfile.objects.get_or_create(
            telegram_id=courier_tg_id,
            defaults={"accepting_orders": True},
        )
        return Response(CourierProfileSerializer(profile).data)


class OrderCancelByStaffView(APIView):
    """POST /api/bot/orders/<pk>/cancel/

    Courier or picker cancels an order with a reason.
    Triggers payment cancel/refund and 1C notification.
    """

    permission_classes = [ApiKeyPermission]

    CANCELLABLE_STATUSES = ("new", "accepted", "assembly", "ready", "delivery", "arrived")

    def post(self, request, pk):
        reason = (request.data.get("reason") or "").strip() or None
        role = (request.data.get("role") or "courier").strip()
        courier_tg_id = request.data.get("courier_tg_id")

        valid_reasons = {c[0] for c in Order.CANCEL_REASON_CHOICES}
        if reason and reason not in valid_reasons:
            return Response(
                {"detail": f"Invalid reason. Allowed: {sorted(valid_reasons)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(pk=pk)
            except Order.DoesNotExist:
                return Response(
                    {"detail": "Order not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if order.status not in self.CANCELLABLE_STATUSES:
                return Response(
                    {"detail": "Order cannot be canceled in current status."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verify courier is assigned to this order (if courier_tg_id provided)
            if courier_tg_id and order.delivered_by and int(courier_tg_id) != order.delivered_by:
                return Response(
                    {"detail": "You are not assigned to this order."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            order.status = "canceled"
            order.canceled_by = role if role in ("courier", "picker") else "courier"
            order.cancel_reason = reason
            order._skip_signal_notification = True
            order.save(update_fields=["status", "canceled_by", "cancel_reason"])

            oid = order.id

            if order.payment_id and order.payment_status in ("authorized", "captured"):
                from apps.integrations.payments.tasks import cancel_payment_task
                transaction.on_commit(lambda: cancel_payment_task.delay(oid))

            if order.onec_guid or order.sync_status in ("sent", "confirmed"):
                from apps.integrations.onec.tasks import notify_onec_order_canceled
                transaction.on_commit(lambda: notify_onec_order_canceled.delay(oid))

            # Send push notification to client
            from apps.notifications.tasks import send_order_push_task
            transaction.on_commit(lambda: send_order_push_task.delay(oid, "delivery", "canceled"))

        return Response({"status": "ok", "order_id": pk, "canceled_by": order.canceled_by})


class OrderReassignView(APIView):
    """POST /api/bot/orders/<pk>/reassign/

    Courier transfers an order (status=ready) to another courier via round-robin.
    Clears delivered_by and triggers assign_courier_task.
    """

    permission_classes = [ApiKeyPermission]

    def post(self, request, pk):
        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(pk=pk)
            except Order.DoesNotExist:
                return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

            if order.status != "ready":
                return Response(
                    {"detail": "Order must be in 'ready' status to reassign."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if order.delivered_by is None:
                return Response(
                    {"detail": "Order has no assigned courier."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            order.delivered_by = None
            order._skip_signal_notification = True
            order.save(update_fields=["delivered_by"])

        # Clear dedup cache so assign_courier_task can proceed
        from django.core.cache import cache
        cache.delete(f"assign:courier:{pk}")

        from apps.notifications.tasks import assign_courier_task
        assign_courier_task.delay(pk)

        return Response({"status": "ok", "order_id": pk})


class CourierToggleAcceptingView(APIView):
    """POST /api/bot/courier/toggle-accepting/

    Toggle courier accepting_orders flag.
    If toggled ON and there are unassigned ready orders, triggers redispatch.
    """

    permission_classes = [ApiKeyPermission]

    def post(self, request):
        serializer = CourierToggleAcceptingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        courier_tg_id = serializer.validated_data["courier_tg_id"]
        accepting = serializer.validated_data["accepting"]

        profile, _ = CourierProfile.objects.get_or_create(
            telegram_id=courier_tg_id,
            defaults={"accepting_orders": accepting},
        )
        was_off = not profile.accepting_orders
        if profile.accepting_orders != accepting:
            profile.accepting_orders = accepting
            profile.save(update_fields=["accepting_orders"])

        # Only redispatch when courier actually turned ON (was off → now on)
        if accepting and was_off:
            from apps.notifications.tasks import redispatch_unassigned_orders
            redispatch_unassigned_orders.delay()

        return Response({"accepting_orders": profile.accepting_orders})


# --- Staff management views ---


class StaffCheckView(APIView):
    """GET /api/bot/staff/check/?telegram_id=X&role=courier|picker

    Returns status: approved, pending, blacklisted, or 404.
    """

    permission_classes = [ApiKeyPermission]

    def get(self, request):
        telegram_id = request.query_params.get("telegram_id")
        role = request.query_params.get("role")

        if not telegram_id or not role:
            return Response(
                {"detail": "telegram_id and role query params are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            telegram_id = int(telegram_id)
        except (ValueError, TypeError):
            return Response(
                {"detail": "telegram_id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Model = CourierProfile if role == "courier" else PickerProfile
        try:
            profile = Model.objects.get(telegram_id=telegram_id)
        except Model.DoesNotExist:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if profile.is_blacklisted:
            return Response({"status": "blacklisted"})
        if profile.is_approved:
            return Response({"status": "approved"})
        return Response({"status": "pending"})


class StaffRegisterView(APIView):
    """POST /api/bot/staff/register/

    Creates a CourierProfile or PickerProfile with is_approved=False.
    """

    permission_classes = [ApiKeyPermission]

    def post(self, request):
        serializer = StaffRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        role = data["role"]
        Model = CourierProfile if role == "courier" else PickerProfile

        profile, created = Model.objects.get_or_create(
            telegram_id=data["telegram_id"],
            defaults={
                "full_name": data["full_name"],
                "phone": data["phone"],
                "is_approved": False,
            },
        )

        if not created:
            # Update existing profile data
            profile.full_name = data["full_name"]
            profile.phone = data["phone"]
            profile.save(update_fields=["full_name", "phone"])

        return Response(
            {
                "telegram_id": profile.telegram_id,
                "full_name": profile.full_name,
                "phone": profile.phone,
                "is_approved": profile.is_approved,
                "is_blacklisted": profile.is_blacklisted,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CourierPhoneView(APIView):
    """GET /api/bot/orders/<pk>/courier-phone/

    Returns courier phone number for the assigned courier.
    """

    permission_classes = [ApiKeyPermission]

    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not order.delivered_by:
            return Response(
                {"detail": "No courier assigned."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            courier = CourierProfile.objects.get(telegram_id=order.delivered_by)
        except CourierProfile.DoesNotExist:
            return Response(
                {"detail": "Courier profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not courier.phone:
            return Response(
                {"detail": "Courier has no phone number."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"phone": courier.phone})


class OrderUpdateStatusView(APIView):
    """POST /api/bot/orders/<pk>/update-status/

    Bot endpoint for changing order status.
    Uses the same core state machine as /onec/order/status,
    but with ApiKeyPermission (no IP whitelist).
    """

    permission_classes = [ApiKeyPermission]

    def post(self, request, pk):
        from apps.orders.services import (
            VALID_STATUSES,
            AlreadyAccepted,
            InvalidTransition,
            update_order_status,
        )

        new_status = (request.data.get("status") or "").strip()
        if not new_status:
            return Response(
                {"detail": "status is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if new_status not in VALID_STATUSES:
            return Response(
                {"detail": f"Invalid status. Allowed: {sorted(VALID_STATUSES)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_assembler = request.data.get("assembler_id")
        raw_courier = request.data.get("courier_id")
        cancel_reason = (request.data.get("cancel_reason") or "").strip() or None
        canceled_by = (request.data.get("canceled_by") or "").strip() or None

        try:
            assembler_id = int(raw_assembler) if raw_assembler is not None else None
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid assembler_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            courier_id = int(raw_courier) if raw_courier is not None else None
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid courier_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                o, previous_status = update_order_status(
                    order_id=pk,
                    new_status=new_status,
                    assembler_id=assembler_id,
                    courier_id=courier_id,
                    cancel_reason=cancel_reason,
                    canceled_by=canceled_by,
                )
        except InvalidTransition:
            return Response(
                {"detail": f"Transition {new_status} not allowed."},
                status=status.HTTP_409_CONFLICT,
            )
        except AlreadyAccepted as exc:
            return Response(
                {"detail": f"Already accepted by assembler {exc.assembled_by}."},
                status=status.HTTP_409_CONFLICT,
            )
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"status": "ok", "order_id": pk, "new_status": o.status},
            status=status.HTTP_200_OK,
        )
