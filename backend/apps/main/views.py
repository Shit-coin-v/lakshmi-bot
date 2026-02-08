from __future__ import annotations

import logging

from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import ApiKeyPermission, CustomerPermission
from apps.main.serializers import CustomerProfileSerializer
from apps.main.models import CustomUser

logger = logging.getLogger(__name__)


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """Получение и обновление профиля клиента."""

    queryset = CustomUser.objects.all()
    serializer_class = CustomerProfileSerializer
    permission_classes = [CustomerPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        obj = super().get_object()
        if obj.pk != self.request.telegram_user.pk:
            self.permission_denied(self.request, message="Нет доступа к чужому профилю")
        return obj


class SendMessageAPIView(APIView):
    """Queue a Telegram message for async delivery via Celery (C11)."""

    permission_classes = [ApiKeyPermission]

    def post(self, request):
        telegram_id = request.data.get("telegram_id")
        text = request.data.get("text")

        if not telegram_id or not text:
            return Response(
                {"err": "telegram_id and text are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = CustomUser.objects.get(telegram_id=telegram_id)
        except CustomUser.DoesNotExist:
            return Response({"err": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        from apps.main.tasks import send_telegram_message_task

        send_telegram_message_task.delay(user.telegram_id, text)

        return Response({"msg": "Message queued."}, status=status.HTTP_200_OK)
