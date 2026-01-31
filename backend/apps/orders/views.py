from __future__ import annotations

from rest_framework import filters, generics
from rest_framework.permissions import AllowAny

from apps.api.serializers import OrderCreateSerializer, OrderListSerializer
from apps.orders.serializers import OrderDetailSerializer, ProductListSerializer
from apps.main.models import Order, Product


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
