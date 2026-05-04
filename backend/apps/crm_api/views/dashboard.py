from rest_framework.response import Response

from apps.crm_api.services.dashboard import compute_dashboard
from apps.crm_api.views._base import CRMAPIView


class DashboardView(CRMAPIView):
    """GET /api/crm/dashboard/ — агрегаты для главной страницы CRM.

    Кэш 5 минут (см. compute_dashboard)."""

    def get(self, request):
        return Response(compute_dashboard())
