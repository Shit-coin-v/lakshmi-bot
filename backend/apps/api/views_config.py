from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.services import get_delivery_price


class AppConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "delivery_price": str(get_delivery_price()),
        })
