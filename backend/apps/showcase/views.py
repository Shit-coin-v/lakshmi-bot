from __future__ import annotations

from django.db.models import (
    Case,
    DecimalField,
    F,
    FloatField,
    IntegerField,
    Q,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.main.models import Product
from apps.orders.serializers import ProductListSerializer


class ShowcaseView(generics.ListAPIView):
    """Предрассчитанная витрина для главной страницы.

    Сортировка:
    1. Товары в наличии (stock > 0) — вверху.
    2. Внутри групп — по предрассчитанному score DESC.
    3. Товары без наличия — внизу.
    4. Fallback при пустом ranking — по pk.
    """

    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        from django.db.models import FilteredRelation

        qs = Product.objects.filter(is_active=True)

        # LEFT JOIN product_rankings с условием customer_id IS NULL
        qs = qs.annotate(
            _global_ranking=FilteredRelation(
                "rankings",
                condition=Q(rankings__customer__isnull=True),
            ),
        )

        # stock: NULL → 0, затем бинарный флаг наличия
        # ranking_score: из JOIN, NULL → 0.0
        qs = qs.annotate(
            _stock=Coalesce("stock", Value(0), output_field=DecimalField()),
            _in_stock=Case(
                When(_stock__gt=0, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            _ranking_score=Coalesce(
                F("_global_ranking__score"),
                Value(0.0),
                output_field=FloatField(),
            ),
        )

        return qs.order_by("-_in_stock", "-_ranking_score", "pk")
