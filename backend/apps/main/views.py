from __future__ import annotations

import logging
import requests
from django.conf import settings

from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.serializers import CustomerProfileSerializer
from apps.main.models import CustomUser

logger = logging.getLogger(__name__)


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """Получение и обновление профиля клиента."""

    queryset = CustomUser.objects.all()
    serializer_class = CustomerProfileSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class SendMessageAPIView(APIView):
    """Minimal wrapper to send a Telegram message on behalf of the bot."""

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

        if not settings.BOT_TOKEN:
            logger.error("BOT_TOKEN is not configured; cannot send message")
            return Response(
                {"err": "Bot token is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        telegram_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": user.telegram_id,
            "text": text,
            "parse_mode": "HTML",
        }

        try:
            response = requests.post(telegram_url, json=payload, timeout=5)
            response.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover
            logger.warning("Failed to send Telegram message: %s", exc)
            return Response(
                {"err": "Failed to send message to Telegram."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"msg": "Message sent successfully."}, status=status.HTTP_200_OK)
