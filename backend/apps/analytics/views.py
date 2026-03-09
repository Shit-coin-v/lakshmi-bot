from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import CustomerPermission

from .serializers import AnalyticsEventSerializer


class AnalyticsEventView(APIView):
    permission_classes = [CustomerPermission]

    def post(self, request):
        serializer = AnalyticsEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.telegram_user)
        return Response(status=status.HTTP_201_CREATED)
