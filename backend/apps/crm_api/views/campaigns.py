"""View для списка кампаний CRM."""
from django.db.models import Count, Q
from rest_framework.generics import ListAPIView

from apps.campaigns.models import Campaign
from apps.crm_api.pagination import CRMHeaderPagination
from apps.crm_api.serializers.campaign import CampaignListSerializer
from apps.crm_api.views._base import CRMAPIView


class CampaignListView(ListAPIView, CRMAPIView):
    """GET /api/crm/campaigns/?status=&page=&page_size= — кампании CRM."""

    serializer_class = CampaignListSerializer
    pagination_class = CRMHeaderPagination

    def get_queryset(self):
        qs = (
            Campaign.objects
            .select_related("segment")
            .prefetch_related("rules")
            .annotate(
                reach=Count("assignments", distinct=True),
                used=Count("assignments", filter=Q(assignments__used=True), distinct=True),
            )
            .order_by("-priority", "-id")
        )
        status = self.request.query_params.get("status", "").strip()
        if status == "active":
            qs = qs.filter(is_active=True)
        elif status == "finished":
            qs = qs.filter(is_active=False)
        # status == "all" / "" — без фильтра
        return qs
