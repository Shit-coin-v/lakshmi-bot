from rest_framework.authentication import SessionAuthentication
from rest_framework.views import APIView

from apps.crm_api.permissions import IsCRMStaff


class CRMAPIView(APIView):
    """Базовый класс для всех CRM-эндпоинтов.

    Авторизация: только session-cookie (никаких JWT/X-Api-Key — это другие
    зоны API). Доступ: только staff-пользователи (is_staff=True).

    authenticate_header возвращает 'Session', чтобы DRF возвращал 401 (а не
    403) для анонимных запросов. По умолчанию SessionAuthentication не
    переопределяет authenticate_header → DRF понижал NotAuthenticated до 403.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsCRMStaff]

    def get_authenticate_header(self, request):
        return "Session"
