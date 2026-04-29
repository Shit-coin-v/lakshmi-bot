from __future__ import annotations

from rest_framework import filters, generics
from rest_framework.permissions import AllowAny

from apps.common.authentication import JWTAuthentication
from apps.main.models import Product
from apps.main.services.catalog_filters import (
    get_hidden_category_ids,
    request_can_view_hidden,
)
from apps.orders.serializers import ProductListSerializer
from apps.showcase.services import apply_storefront_ordering


class ShowcaseView(generics.ListAPIView):
    """Предрассчитанная витрина для главной страницы.

    Сортировка делегирована в apply_storefront_ordering — общий хелпер,
    который используется и в /api/products/ для согласованного UX.

    1. Товары в наличии (stock > 0) — вверху.
    2. Внутри групп — по предрассчитанному score DESC.
    3. Tie-breaker — по pk.

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

        # Скрытые категории — товары из них не должны попадать в витрину
        # и в персональные рекомендации. Staff-bypass (`?include_hidden=true`
        # + X-Api-Key) для витрины тоже работает.
        if not request_can_view_hidden(self.request):
            hidden_ids = get_hidden_category_ids()
            if hidden_ids:
                qs = qs.exclude(category_id__in=hidden_ids)

        return apply_storefront_ordering(qs, self.request)
