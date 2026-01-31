from __future__ import annotations

from rest_framework import filters, generics
from rest_framework.permissions import AllowAny

from apps.orders.serializers import OrderDetailSerializer, ProductListSerializer
from apps.main.models import Order, Product


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]

    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]


class OrderDetailView(generics.RetrieveAPIView):
    queryset = Order.objects.all().prefetch_related("items__product")
    serializer_class = OrderDetailSerializer
    permission_classes = [AllowAny]
