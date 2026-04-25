from __future__ import annotations

import logging
import time

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.authentication import JWTAuthentication
from apps.common.permissions import ApiKeyPermission, CustomerPermission
from apps.common.throttling import ProductImageUploadThrottle
from apps.main.models import CustomUser, Product
from apps.main.serializers import CustomerProfileSerializer
from apps.main.services.image_processor import (
    ImageProcessingError,
    process_product_image,
)

logger = logging.getLogger(__name__)


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """Customer profile: retrieve and update."""

    serializer_class = CustomerProfileSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return CustomUser.objects.filter(pk=self.request.telegram_user.pk)


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


class ProductImageUploadView(APIView):
    """Загрузка фото товара с обработкой через OpenAI Image API.

    Контракт ``POST /api/products/<int:pk>/image/``:

    - авторизация — ``X-Api-Key`` (``ApiKeyPermission``);
    - тело — ``multipart/form-data``, поле ``image``;
    - 200 — товар обновлён, ответ содержит ``image_url`` обработанного фото;
    - 400 — пустой/некорректный файл; 404 — товар не найден;
    - 413 — файл больше ``PRODUCT_IMAGE_MAX_UPLOAD_SIZE``;
    - 415 — формат вне ``PRODUCT_IMAGE_ALLOWED_FORMATS``;
    - 502 — OpenAI вернул ошибку; финальное фото при этом не перезаписывается.

    Файл в обработанном виде кладётся в ``MEDIA_ROOT/products/`` через
    стандартное Django-хранилище. RAW-исходник нигде не сохраняется:
    его байты живут только в памяти процесса до вызова OpenAI.
    """

    authentication_classes: list = []
    permission_classes = [ApiKeyPermission]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [ProductImageUploadThrottle]

    def post(self, request, pk: int):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response(
                {"detail": "Товар не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )

        upload = request.FILES.get("image")
        if upload is None:
            return Response(
                {"detail": "Файл изображения обязателен в поле 'image'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if upload.size in (None, 0):
            return Response(
                {"detail": "Пустой файл"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        max_size = int(
            getattr(settings, "PRODUCT_IMAGE_MAX_UPLOAD_SIZE", 10 * 1024 * 1024)
        )
        if upload.size > max_size:
            mb = max_size // (1024 * 1024)
            return Response(
                {"detail": f"Файл слишком большой. Максимум: {mb} МБ"},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        allowed_formats = {
            f.lower().lstrip(".")
            for f in getattr(
                settings,
                "PRODUCT_IMAGE_ALLOWED_FORMATS",
                ["jpg", "jpeg", "png", "webp"],
            )
        }
        suffix = (upload.name.rsplit(".", 1)[-1] if "." in upload.name else "").lower()
        content_type = (upload.content_type or "").lower()
        # MIME-тип может приехать пустым из мобильных браузеров — тогда
        # ориентируемся только на расширение.
        allowed_mimes = {f"image/{f}" for f in allowed_formats} | {"image/jpeg"}
        if suffix not in allowed_formats and content_type not in allowed_mimes:
            return Response(
                {
                    "detail": (
                        "Недопустимый формат файла. Допустимы: "
                        + ", ".join(sorted(allowed_formats))
                    )
                },
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        # Считываем RAW в память: на диск не пишем ни в каком виде.
        raw_bytes = upload.read()
        mime = content_type or f"image/{suffix or 'png'}"

        try:
            processed_bytes = process_product_image(
                raw_bytes,
                mime_type=mime,
                filename=upload.name or "photo",
            )
        except ImageProcessingError as exc:
            logger.warning(
                "OpenAI image processing failed product_id=%s: %s",
                product.pk,
                exc,
            )
            return Response(
                {"detail": "Не удалось обработать фото. Попробуйте позже."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not processed_bytes:
            return Response(
                {"detail": "OpenAI вернул пустое изображение"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Старое фото удаляем, чтобы не копить мусор в MEDIA_ROOT/products/.
        if product.image:
            product.image.delete(save=False)

        identifier = product.product_code or str(product.pk)
        safe_id = slugify(identifier) or str(product.pk)
        target_name = f"{safe_id}_{int(time.time())}.png"

        product.image.save(target_name, ContentFile(processed_bytes), save=False)
        product.updated_at = timezone.now()
        product.save(update_fields=["image", "updated_at"])

        return Response(
            {
                "id": product.pk,
                "product_code": product.product_code,
                "name": product.name,
                "image_url": product.image.url if product.image else None,
                "updated_at": (
                    product.updated_at.isoformat() if product.updated_at else None
                ),
            },
            status=status.HTTP_200_OK,
        )
