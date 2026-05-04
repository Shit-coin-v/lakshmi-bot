from django.db.models import Count, Q
from rest_framework.generics import ListAPIView

from apps.crm_api.pagination import CRMHeaderPagination
from apps.crm_api.serializers.broadcast import BroadcastHistorySerializer
from apps.crm_api.views._base import CRMAPIView
from apps.main.models import BroadcastMessage


class BroadcastHistoryView(ListAPIView, CRMAPIView):
    """GET /api/crm/broadcasts/history/?page=&page_size= — история рассылок."""

    serializer_class = BroadcastHistorySerializer
    pagination_class = CRMHeaderPagination

    def get_queryset(self):
        return (
            BroadcastMessage.objects
            .annotate(
                reach=Count("deliveries", distinct=True),
                opened=Count("deliveries", filter=Q(deliveries__opened_at__isnull=False), distinct=True),
            )
            .order_by("-created_at")
        )
