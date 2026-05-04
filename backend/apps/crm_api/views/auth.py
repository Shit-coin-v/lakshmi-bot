from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.throttling import AnonAuthThrottle
from apps.crm_api.serializers.auth import LoginSerializer, MeSerializer
from apps.crm_api.views._base import CRMAPIView

User = get_user_model()


class LoginView(APIView):
    """POST /api/crm/auth/login/ — вход менеджера по email + password.

    На успех:
    - проставляется session-cookie (sessionid)
    - проставляется csrftoken-cookie (для будущих POST/PATCH/DELETE)
    - в ответе: {"user": {id, email, name}}
    Ошибки:
    - 400 — невалидный body
    - 401 — пользователь не найден или неверный пароль
    - 403 — найден, но is_staff=False
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonAuthThrottle]

    @method_decorator(ensure_csrf_cookie)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]

        user = User.objects.filter(email__iexact=email).first()
        if not user or not check_password(password, user.password):
            return Response(
                {"detail": "Неверный email или пароль"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_staff:
            return Response(
                {"detail": "Нет доступа в CRM"},
                status=status.HTTP_403_FORBIDDEN,
            )

        django_login(request, user)
        return Response({"user": MeSerializer(user).data})


class LogoutView(CRMAPIView):
    """POST /api/crm/auth/logout/ — выход менеджера.

    Снимает session-cookie. Без тела запроса/ответа (204).
    """

    def post(self, request):
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(CRMAPIView):
    """GET /api/crm/auth/me/ — кто я.

    Возвращает {"user": {...}} если живая сессия, иначе 401 (через permission).
    Также проставляет csrftoken для будущих POST'ов.
    """

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"user": MeSerializer(request.user).data})
