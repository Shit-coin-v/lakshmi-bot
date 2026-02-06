from __future__ import annotations

from rest_framework import filters, generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

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
    permission_classes = [AllowAny]


class OrderDetailView(generics.RetrieveAPIView):
    queryset = Order.objects.all().prefetch_related("items__product")
    serializer_class = OrderDetailSerializer
    permission_classes = [AllowAny]


class OrderListUserView(generics.ListAPIView):
    serializer_class = OrderListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")

        if user_id:
            return Order.objects.filter(customer_id=user_id).order_by("-created_at")

        return Order.objects.none()


class OrderCancelView(APIView):
    permission_classes = [AllowAny]

    CANCELLABLE_STATUSES = ("new", "assembly")

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Заказ не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.status not in self.CANCELLABLE_STATUSES:
            return Response(
                {"detail": "Заказ нельзя отменить в текущем статусе"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous_status = order.status
        order.status = "canceled"
        order.save(update_fields=["status"])

        from apps.notifications.push import notify_order_status_change
        notify_order_status_change(order, previous_status=previous_status)

        return Response({"detail": "Заказ отменён"})
