from django.db.models import Count, Q
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView, RetrieveAPIView

from apps.crm_api.serializers.category import CategoryDetailSerializer, CategoryListSerializer
from apps.crm_api.views._base import CRMAPIView
from apps.main.models import Category


class CategoryListView(ListAPIView, CRMAPIView):
    """GET /api/crm/categories/ — без пагинации (категорий обычно <100)."""

    serializer_class = CategoryListSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Category.objects.filter(is_active=True)
            .annotate(skus=Count("products", filter=Q(products__is_active=True)))
            .order_by("sort_order", "name")
        )


class CategoryDetailView(RetrieveAPIView, CRMAPIView):
    """GET /api/crm/categories/<slug>/ — карточка категории + SKU."""

    serializer_class = CategoryDetailSerializer

    def get_object(self):
        slug = self.kwargs["slug"]
        if not slug.startswith("cat-"):
            raise NotFound("Категория не найдена")
        ext = slug[4:]
        qs = (
            Category.objects.filter(is_active=True)
            .annotate(skus=Count("products", filter=Q(products__is_active=True)))
            .prefetch_related("products")
        )
        cat = qs.filter(external_id=ext).first()
        if cat is None and ext.isdigit():
            cat = qs.filter(id=int(ext)).first()
        if cat is None:
            raise NotFound("Категория не найдена")
        return cat
