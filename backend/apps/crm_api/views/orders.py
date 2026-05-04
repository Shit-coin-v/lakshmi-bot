from django.db.models import Count
from rest_framework.generics import ListAPIView

from apps.crm_api.pagination import CRMHeaderPagination
from apps.crm_api.serializers.order import OrderListSerializer
from apps.crm_api.views._base import CRMAPIView
from apps.orders.models import Order


class OrderListView(ListAPIView, CRMAPIView):
    """GET /api/crm/orders/?status=&purchaseType=&page=&page_size= — заказы CRM."""

    serializer_class = OrderListSerializer
    pagination_class = CRMHeaderPagination

    def get_queryset(self):
        qs = (
            Order.objects
            .select_related("customer")
            .annotate(_prefetched_items_count=Count("items"))
            .order_by("-created_at")
        )
        status = self.request.query_params.get("status", "").strip()
        ptype = self.request.query_params.get("purchaseType", "").strip()
        if status and status != "Все":
            qs = qs.filter(status=status)
        if ptype and ptype != "Все":
            qs = qs.filter(fulfillment_type=ptype)
        return qs
