import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import HeaderPagination
from apps.common.permissions import CustomerPermission
from .models import CustomerDevice
from .models import Notification, NotificationOpenEvent
from apps.notifications.serializers import (
    NotificationSerializer,
)

logger = logging.getLogger(__name__)


class NotificationViewSet(viewsets.ViewSet):
    permission_classes = [CustomerPermission]

    def list(self, request):
        qs = Notification.objects.filter(user=request.telegram_user).order_by("-created_at")
        paginator = HeaderPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                NotificationSerializer(page, many=True).data
            )
        return Response(NotificationSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        try:
            n = Notification.objects.get(pk=int(pk), user=request.telegram_user)
        except Notification.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(NotificationSerializer(n).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        cnt = Notification.objects.filter(user=request.telegram_user, is_read=False).count()
        return Response({"unread_count": cnt}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="read-all")
    def mark_all_read(self, request):
        updated = Notification.objects.filter(
            user=request.telegram_user, is_read=False
        ).update(is_read=True)
        return Response({"status": "ok", "updated_count": updated}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        source = (request.data.get("source") or "inapp")
        if source not in {"inapp", "push"}:
            source = "inapp"

        try:
            n = Notification.objects.get(pk=int(pk), user=request.telegram_user)
        except Notification.DoesNotExist:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)

        from django.utils import timezone

        now = timezone.now()
        time_to_open = now - n.created_at if n.created_at else None

        NotificationOpenEvent.objects.create(
            notification=n,
            user=request.telegram_user,
            source=source,
            time_to_open=time_to_open,
        )

        if not n.is_read:
            n.is_read = True
            n.save(update_fields=["is_read"])

        cnt = Notification.objects.filter(user=request.telegram_user, is_read=False).count()
        return Response({"status": "ok", "unread_count": cnt}, status=status.HTTP_200_OK)


def _register_device(request):
    """Extract FCM token from request and upsert CustomerDevice. Returns (device, created, error)."""
    fcm_token = (request.data.get("fcm_token") or "").strip()
    platform = (request.data.get("platform") or "android").lower()
    if not fcm_token:
        return None, None, "fcm_token is required"
    customer = request.telegram_user
    device, created = CustomerDevice.objects.update_or_create(
        fcm_token=fcm_token,
        defaults={"customer": customer, "platform": platform},
    )
    return device, created, None


class UpdateFCMTokenView(APIView):
    permission_classes = [CustomerPermission]

    def post(self, request):
        device, created, error = _register_device(request)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"status": "ok", "device_id": device.id, "created": created},
            status=status.HTTP_200_OK,
        )


class PushRegisterView(APIView):
    permission_classes = [CustomerPermission]

    def post(self, request):
        device, created, error = _register_device(request)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
        logger.info(
            "Registered FCM token for customer=%s | platform=%s | created=%s",
            request.telegram_user.id,
            (request.data.get("platform") or "android").lower(),
            created,
        )
        return Response({"status": "ok", "device_id": device.id}, status=status.HTTP_200_OK)
