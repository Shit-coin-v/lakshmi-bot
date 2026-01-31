from __future__ import annotations

from rest_framework import generics
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny

from apps.api.serializers import CustomerProfileSerializer
from apps.main.models import CustomUser


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """Получение и обновление профиля клиента."""

    queryset = CustomUser.objects.all()
    serializer_class = CustomerProfileSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
