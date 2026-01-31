from __future__ import annotations

from rest_framework import filters, generics
from rest_framework.permissions import AllowAny

from apps.orders.serializers import ProductListSerializer
from apps.main.models import Product


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]

    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]
