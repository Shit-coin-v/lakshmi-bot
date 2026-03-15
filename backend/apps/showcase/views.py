from __future__ import annotations

from django.conf import settings as django_settings
from django.db.models import (
    Case,
    DecimalField,
    F,
    FilteredRelation,
    FloatField,
    IntegerField,
    Q,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from rest_framework import filters, generics
from rest_framework.permissions import AllowAny

from apps.common.authentication import JWTAuthentication
from apps.main.models import CustomUser, Product
from apps.orders.serializers import ProductListSerializer


class ShowcaseView(generics.ListAPIView):
    """Предрассчитанная витрина для главной страницы.

    Сортировка:
    1. Товары в наличии (stock > 0) — вверху.
    2. Внутри групп — по предрассчитанному score DESC.
    3. Товары без наличия — внизу.
    4. Fallback при пустом ranking — по pk.

    Персонализация (при PERSONAL_RANKING_ENABLED=True):
    - Авторизованный клиент получает Coalesce(personal, global, 0.0).
    - Анонимный или kill-switch=off — только global ranking.
    """

    serializer_class = ProductListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True)

        use_personal = (
            getattr(django_settings, "PERSONAL_RANKING_ENABLED", False)
            and isinstance(self.request.user, CustomUser)
        )

        if use_personal:
            qs = qs.annotate(
                _personal_ranking=FilteredRelation(
                    "rankings",
                    condition=Q(rankings__customer=self.request.user),
                ),
                _global_ranking=FilteredRelation(
                    "rankings",
                    condition=Q(rankings__customer__isnull=True),
                ),
            )
            ranking_score = Coalesce(
                F("_personal_ranking__score"),
                F("_global_ranking__score"),
                Value(0.0),
                output_field=FloatField(),
            )
        else:
            qs = qs.annotate(
                _global_ranking=FilteredRelation(
                    "rankings",
                    condition=Q(rankings__customer__isnull=True),
                ),
            )
            ranking_score = Coalesce(
                F("_global_ranking__score"),
                Value(0.0),
                output_field=FloatField(),
            )

        qs = qs.annotate(
            _stock=Coalesce("stock", Value(0), output_field=DecimalField()),
            _in_stock=Case(
                When(_stock__gt=0, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            _ranking_score=ranking_score,
        )

        return qs.order_by("-_in_stock", "-_ranking_score", "pk")
