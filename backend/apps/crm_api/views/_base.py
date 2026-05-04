from rest_framework.authentication import SessionAuthentication
from rest_framework.views import APIView

from apps.crm_api.permissions import IsCRMStaff


class CRMAPIView(APIView):
    """Базовый класс для всех CRM-эндпоинтов.

    Авторизация: только session-cookie (никаких JWT/X-Api-Key — это другие
    зоны API). Доступ: только staff-пользователи (is_staff=True).
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsCRMStaff]
