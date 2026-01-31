import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import ApiKeyPermission
from apps.main.models import CustomUser, CustomerDevice, Notification, NotificationOpenEvent
from apps.notifications.serializers import (
    NotificationReadSerializer,
    NotificationSerializer,
    UpdateFCMTokenSerializer,
)

logger = logging.getLogger(__name__)


class NotificationViewSet(viewsets.ViewSet):
    permission_classes = []
    authentication_classes = []

    def _check_api_key(self, request):
        perm = ApiKeyPermission()
        if not perm.has_permission(request, self):
            raise PermissionDenied("Forbidden")

    def list(self, request):
        self._check_api_key(request)

        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response([], status=200)

        qs = (
            Notification.objects
            .filter(user_id=int(user_id))
            .order_by("-created_at")
        )
        return Response(NotificationSerializer(qs, many=True).data, status=200)

    def retrieve(self, request, pk=None):
        self._check_api_key(request)

        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"detail": "user_id is required"}, status=400)

        try:
            n = Notification.objects.get(pk=int(pk), user_id=int(user_id))
        except Notification.DoesNotExist:
            return Response({"detail": "not found"}, status=404)

        return Response(NotificationSerializer(n).data, status=200)

    def read(self, request, pk=None):
        perm = ApiKeyPermission()
        if not perm.has_permission(request, self):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get("user_id") or request.query_params.get("user_id")
        if not user_id:
            return Response({"detail": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            notif = Notification.objects.select_related("user").get(
                pk=int(pk),
                user_id=int(user_id),
            )
        except (TypeError, ValueError):
            return Response({"detail": "invalid id"}, status=status.HTTP_400_BAD_REQUEST)
        except Notification.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        if not notif.is_read:
            notif.is_read = True
            notif.save(update_fields=["is_read"])

        try:
            source = (request.data.get("source") or request.query_params.get("source") or "inapp")
            if source not in {"inapp", "push"}:
                source = "inapp"

            NotificationOpenEvent.objects.get_or_create(
                notification=notif,
                user=notif.user,
                defaults={"source": source},
            )
        except Exception:
            logger.exception("Failed to log notification open event notification_id=%s", notif.id)

        return Response({"status": "ok", "id": notif.id, "is_read": True}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        self._check_api_key(request)

        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response({"unread_count": 0}, status=200)

        cnt = Notification.objects.filter(user_id=int(user_id), is_read=False).count()
        return Response({"unread_count": cnt}, status=200)

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        self._check_api_key(request)

        s = NotificationReadSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        user_id = int(s.validated_data["user_id"])
        source = s.validated_data.get("source") or "inapp"

        try:
            n = Notification.objects.get(pk=int(pk), user_id=user_id)
        except Notification.DoesNotExist:
            return Response({"detail": "not found"}, status=404)

        NotificationOpenEvent.objects.get_or_create(
            notification=n,
            defaults={"user_id": user_id, "source": source},
        )

        if not n.is_read:
            n.is_read = True
            n.save(update_fields=["is_read"])

        cnt = Notification.objects.filter(user_id=user_id, is_read=False).count()
        return Response({"status": "ok", "unread_count": cnt}, status=200)


class UpdateFCMTokenView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        perm = ApiKeyPermission()
        if not perm.has_permission(request, self):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        s = UpdateFCMTokenSerializer(data=request.data)
        if not s.is_valid():
            return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

        customer_id = int(s.validated_data["customer_id"])
        fcm_token = s.validated_data["fcm_token"].strip()
        platform = s.validated_data.get("platform", "android")

        try:
            customer = CustomUser.objects.get(id=customer_id)
        except CustomUser.DoesNotExist:
            return Response({"detail": "customer not found"}, status=status.HTTP_404_NOT_FOUND)

        device, created = CustomerDevice.objects.update_or_create(
            fcm_token=fcm_token,
            defaults={"customer": customer, "platform": platform},
        )

        return Response(
            {"status": "ok", "device_id": device.id, "created": created},
            status=status.HTTP_200_OK,
        )


class PushRegisterView(APIView):
    # ApiKeyPermission у тебя уже завязан на X-Api-Key 👍
    permission_classes = []  # НЕ ставим DRF-auth; проверка только через ApiKeyPermission ниже
    authentication_classes = []

    def post(self, request):
        # ручная проверка через permission класс
        perm = ApiKeyPermission()
        if not perm.has_permission(request, self):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        fcm_token = (request.data.get("fcm_token") or "").strip()
        platform = (request.data.get("platform") or "android").lower()
        customer_id = request.data.get("customer_id")

        if not fcm_token or not customer_id:
            return Response(
                {"detail": "customer_id and fcm_token are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            customer = CustomUser.objects.get(id=int(customer_id))
        except (TypeError, ValueError, CustomUser.DoesNotExist):
            return Response({"detail": "customer not found"}, status=status.HTTP_404_NOT_FOUND)

        device, created = CustomerDevice.objects.update_or_create(
            fcm_token=fcm_token,
            defaults={"customer": customer, "platform": platform},
        )

        logger.info(
            "Registered FCM token for customer=%s | platform=%s | created=%s",
            customer.id,
            platform,
            created,
        )

        return Response({"status": "ok", "device_id": device.id}, status=status.HTTP_200_OK)
