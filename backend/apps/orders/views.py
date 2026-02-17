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

            order.status = "canceled"
            order.save(update_fields=["status"])

        # Push notification handled by _order_post_save signal
        return Response({"detail": "Заказ отменён"})
