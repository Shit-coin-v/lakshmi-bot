from __future__ import annotations

from django.db import transaction
from django.db.models import Count

from rest_framework import filters, generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import CustomerPermission
from apps.orders.serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    ProductListSerializer,
)
from apps.orders.models import Order, Product


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]

    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]


class OrderCreateView(generics.CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer
    permission_classes = [CustomerPermission]

    def perform_create(self, serializer):
        serializer.save(customer=self.request.telegram_user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        order = serializer.instance

        response_data = {"id": order.id}

        # For SBP payments, include confirmation_url
        confirmation_url = getattr(order, "_confirmation_url", None)
        if confirmation_url:
            response_data["confirmation_url"] = confirmation_url
            response_data["payment_id"] = order.payment_id

        return Response(response_data, status=status.HTTP_201_CREATED)


class OrderDetailView(generics.RetrieveAPIView):
    queryset = Order.objects.all().prefetch_related("items__product")
    serializer_class = OrderDetailSerializer
    permission_classes = [CustomerPermission]

    def get_object(self):
        obj = super().get_object()
        if obj.customer_id != self.request.telegram_user.pk:
            self.permission_denied(self.request, message="Нет доступа к чужому заказу")
        return obj


class OrderListUserView(generics.ListAPIView):
    serializer_class = OrderListSerializer
    permission_classes = [CustomerPermission]

    def get_queryset(self):
        return Order.objects.filter(
            customer=self.request.telegram_user,
        ).annotate(
            items_count=Count("items"),
        ).order_by("-created_at")


class OrderCancelView(APIView):
    permission_classes = [CustomerPermission]

    CANCELLABLE_STATUSES = ("new", "accepted", "assembly", "ready")

    def post(self, request, pk):
        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(pk=pk)
            except Order.DoesNotExist:
                return Response(
                    {"detail": "Заказ не найден"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if order.customer_id != request.telegram_user.pk:
                return Response(
                    {"detail": "Нет доступа к чужому заказу"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if order.status not in self.CANCELLABLE_STATUSES:
                return Response(
                    {"detail": "Заказ нельзя отменить в текущем статусе"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cancel_reason = request.data.get("cancel_reason")
            valid_reasons = {c[0] for c in Order.CANCEL_REASON_CHOICES}
            if cancel_reason and cancel_reason not in valid_reasons:
                cancel_reason = None

            order.status = "canceled"
            order.canceled_by = "client"
            order.cancel_reason = cancel_reason
            order.save(update_fields=["status", "canceled_by", "cancel_reason"])

            oid = order.id

            # Cancel/refund online payment if exists.
            if order.payment_id and order.payment_status in ("authorized", "captured"):
                from apps.integrations.payments.tasks import cancel_payment_task
                transaction.on_commit(lambda: cancel_payment_task.delay(oid))

            # Notify 1C about cancellation (if order was sent to 1C).
            if order.onec_guid or order.sync_status in ("sent", "confirmed"):
                from apps.integrations.onec.tasks import notify_onec_order_canceled
                transaction.on_commit(lambda: notify_onec_order_canceled.delay(oid))

        # Push notification handled by _order_post_save signal
        return Response({"detail": "Заказ отменён"})
