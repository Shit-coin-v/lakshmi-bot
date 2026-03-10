from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import generics

from apps.common.permissions import CustomerPermission

from .models import CampaignRule, CustomerCampaignAssignment
from .serializers import UserAssignedCampaignSerializer


class UserAssignedCampaignsView(generics.ListAPIView):
    """GET /api/campaigns/active/ — активные назначенные кампании текущего пользователя."""

    permission_classes = [CustomerPermission]
    serializer_class = UserAssignedCampaignSerializer

    def get_queryset(self):
        now = timezone.now()
        return (
            CustomerCampaignAssignment.objects.filter(
                customer=self.request.telegram_user,
                campaign__is_active=True,
                campaign__start_at__lte=now,
                campaign__end_at__gte=now,
            )
            .exclude(
                campaign__one_time_use=True,
                used=True,
            )
            .select_related("campaign")
            .prefetch_related(
                Prefetch(
                    "campaign__rules",
                    queryset=CampaignRule.objects.filter(is_active=True),
                )
            )
            .order_by("-campaign__priority", "-campaign__created_at")
        )
