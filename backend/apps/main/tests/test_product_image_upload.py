"""Тесты endpoint загрузки и обработки фото товара через OpenAI.

Покрывают контракт ``POST /api/products/<id>/image/`` из чек-листа задачи:

- успешная загрузка и обработка фото;
- ошибка без файла / при пустом файле;
- ошибка при неверном формате;
- ошибка при слишком большом файле;
- ошибка при несуществующем product_id;
- проверка прав доступа (нет/неверный X-Api-Key);
- ошибка OpenAI API не сохраняет фото;
- сохраняется именно обработанное изображение, а не RAW;
- финальное фото лежит в ``MEDIA_ROOT/products/``;
- обновлённое фото отдаётся в ``/api/products/`` (каталог);
- подмена ``product_code`` в форме не обновляет другой товар.

Фактический вызов OpenAI замокан: тесты гоняют `process_product_image`
как точку расширения, а не реальный сетевой клиент.
"""

from __future__ import annotations

import io
import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.main.models import Product
from apps.main.services.image_processor import ImageProcessingError


def _make_png_bytes(color: tuple[int, int, int] = (255, 200, 100)) -> bytes:
    """Сгенерировать минимальный валидный PNG для тестов."""

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=color).save(buf, format="PNG")
    return buf.getvalue()


_TMP_MEDIA = tempfile.mkdtemp(prefix="lakshmi-test-media-")


def tearDownModule():  # pragma: no cover — служебная очистка
    shutil.rmtree(_TMP_MEDIA, ignore_errors=True)


@override_settings(
    MEDIA_ROOT=_TMP_MEDIA,
    INTEGRATION_API_KEY="test-photo-key",
    OPENAI_API_KEY="test-openai-key",
    PRODUCT_IMAGE_STYLE_PROMPT="test prompt",
    PRODUCT_IMAGE_MAX_UPLOAD_SIZE=1 * 1024 * 1024,
    PRODUCT_IMAGE_ALLOWED_FORMATS=["jpg", "jpeg", "png", "webp"],
    PRODUCT_IMAGE_PROCESSING_TIMEOUT=10,
    PRODUCT_IMAGE_OUTPUT_SIZE="1024x1024",
    PRODUCT_IMAGE_MODEL="gpt-image-1",
)
class ProductImageUploadTests(TestCase):
    """Контракт endpoint POST /api/products/<id>/image/."""

    def setUp(self):
        self.product = Product.objects.create(
            product_code="MLK-032",
            name="Молоко 3.2%",
            price="89.00",
            store_id=1,
        )
        self.url = f"/api/products/{self.product.pk}/image/"
        self.headers = {"HTTP_X_API_KEY": "test-photo-key"}
        self.processed = _make_png_bytes(color=(120, 200, 100))

    def _build_upload(
        self,
        *,
        name: str = "photo.png",
        content: bytes | None = None,
        content_type: str = "image/png",
    ) -> SimpleUploadedFile:
        return SimpleUploadedFile(
            name,
            content if content is not None else _make_png_bytes(),
            content_type=content_type,
        )

    @patch("apps.main.views.process_product_image")
    def test_success_uploads_processed_image(self, mock_process):
        mock_process.return_value = self.processed
        upload = self._build_upload()

        response = self.client.post(
            self.url,
            {"image": upload},
            **self.headers,
        )

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["id"], self.product.pk)
        self.assertEqual(body["product_code"], "MLK-032")
        self.assertTrue(body["image_url"].startswith("/media/products/"))
        self.assertTrue(body["image_url"].endswith(".png"))
        self.assertIsNotNone(body["updated_at"])

        self.product.refresh_from_db()
        self.assertTrue(self.product.image)

        # Сохранён обработанный байт-поток, а не RAW.
        with self.product.image.open("rb") as fh:
            saved = fh.read()
        self.assertEqual(saved, self.processed)

        # Финальный файл лежит в backend/media/products/.
        self.assertTrue(self.product.image.path.startswith(_TMP_MEDIA))
        self.assertIn("/products/", self.product.image.path)

        mock_process.assert_called_once()

    def test_missing_file_returns_400(self):
        response = self.client.post(self.url, {}, **self.headers)
        self.assertEqual(response.status_code, 400)

    def test_empty_file_returns_400(self):
        upload = SimpleUploadedFile("photo.png", b"", content_type="image/png")
        response = self.client.post(
            self.url,
            {"image": upload},
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_format_returns_415(self):
        upload = SimpleUploadedFile(
            "not-image.txt", b"hello world", content_type="text/plain"
        )
        response = self.client.post(
            self.url,
            {"image": upload},
            **self.headers,
        )
        self.assertEqual(response.status_code, 415)

    def test_too_large_returns_413(self):
        big = b"\x00" * (2 * 1024 * 1024)
        upload = SimpleUploadedFile("big.png", big, content_type="image/png")
        response = self.client.post(
            self.url,
            {"image": upload},
            **self.headers,
        )
        self.assertEqual(response.status_code, 413)

    def test_nonexistent_product_returns_404(self):
        upload = self._build_upload()
        response = self.client.post(
            f"/api/products/{self.product.pk + 9999}/image/",
            {"image": upload},
            **self.headers,
        )
        self.assertEqual(response.status_code, 404)

    def test_missing_api_key_returns_403(self):
        upload = self._build_upload()
        response = self.client.post(self.url, {"image": upload})
        self.assertEqual(response.status_code, 403)

    def test_invalid_api_key_returns_403(self):
        upload = self._build_upload()
        response = self.client.post(
            self.url,
            {"image": upload},
            HTTP_X_API_KEY="wrong-key",
        )
        self.assertEqual(response.status_code, 403)

    @patch("apps.main.views.process_product_image")
    def test_openai_failure_does_not_save_image(self, mock_process):
        mock_process.side_effect = ImageProcessingError("OpenAI is down")
        upload = self._build_upload()

        response = self.client.post(
            self.url,
            {"image": upload},
            **self.headers,
        )
        self.assertEqual(response.status_code, 502)

        self.product.refresh_from_db()
        self.assertFalse(self.product.image)

    @patch("apps.main.views.process_product_image")
    def test_raw_file_is_not_saved_as_final(self, mock_process):
        """Гарантия: исходный байт-поток не подменяет обработанный."""

        raw_bytes = b"RAW-payload-do-not-save-as-final"
        mock_process.return_value = self.processed
        upload = SimpleUploadedFile(
            "photo.png", raw_bytes, content_type="image/png"
        )

        response = self.client.post(
            self.url,
            {"image": upload},
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)

        self.product.refresh_from_db()
        with self.product.image.open("rb") as fh:
            saved = fh.read()
        self.assertEqual(saved, self.processed)
        self.assertNotEqual(saved, raw_bytes)

    @patch("apps.main.views.process_product_image")
    def test_image_url_appears_in_catalog_api(self, mock_process):
        """После загрузки image_url отдаётся в /api/products/."""

        mock_process.return_value = self.processed
        upload = self._build_upload()
        self.client.post(self.url, {"image": upload}, **self.headers)

        self.product.refresh_from_db()
        catalog = self.client.get("/api/products/")
        self.assertEqual(catalog.status_code, 200)

        data = catalog.json()
        match = next((p for p in data if p["id"] == self.product.pk), None)
        self.assertIsNotNone(match)
        self.assertEqual(match["image_url"], self.product.image.url)

    @patch("apps.main.views.process_product_image")
    def test_sku_in_form_does_not_update_other_product(self, mock_process):
        """Подмена product_code в теле формы не обновляет чужой товар."""

        other = Product.objects.create(
            product_code="BRD-014",
            name="Хлеб",
            price="54.00",
            store_id=1,
        )
        mock_process.return_value = self.processed
        upload = self._build_upload()

        response = self.client.post(
            self.url,
            {"image": upload, "product_code": "BRD-014"},
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)

        self.product.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(self.product.image)
        self.assertFalse(other.image)

    @patch("apps.main.views.process_product_image")
    def test_replacing_image_removes_old_file(self, mock_process):
        """При повторной загрузке старый файл удаляется."""

        mock_process.return_value = self.processed
        first = self._build_upload()
        self.client.post(self.url, {"image": first}, **self.headers)

        self.product.refresh_from_db()
        old_path = self.product.image.path
        self.assertTrue(self.product.image.storage.exists(self.product.image.name))

        # Вторая загрузка — другой обработанный байт-поток.
        new_processed = _make_png_bytes(color=(0, 0, 255))
        mock_process.return_value = new_processed
        second = self._build_upload(name="photo2.png")
        self.client.post(self.url, {"image": second}, **self.headers)

        self.product.refresh_from_db()
        with self.product.image.open("rb") as fh:
            self.assertEqual(fh.read(), new_processed)

        # Старый файл удалён с диска.
        import os

        self.assertFalse(os.path.exists(old_path))
