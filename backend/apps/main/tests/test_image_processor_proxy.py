"""Тесты proxy-режима в process_product_image.

Покрытие из чек-листа задачи (Agent 5 / Agent 6):

- proxy-режим включается через OPENAI_USE_PROXY=True;
- backend шлёт POST {base_url}/v1/images/edit с X-Internal-Api-Key;
- multipart содержит image, prompt, model, size;
- 200 + image/png → bytes возвращаются как есть;
- 401/4xx/5xx от proxy → ImageProcessingError;
- timeout/connection error → ImageProcessingError;
- ответ не-image content-type → ImageProcessingError;
- отсутствие base_url или ключа → ImageProcessingError.

Не вызываем реальный OpenAI и реальный сетевой стек — мокаем
``requests.post`` непосредственно.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase, override_settings

from apps.main.services.image_processor import (
    ImageProcessingError,
    process_product_image,
)


def _ok_response(content: bytes = b"PROCESSED_PNG_BYTES") -> MagicMock:
    """Моковый ответ proxy: 200 + image/png."""

    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {"Content-Type": "image/png"}
    resp.content = content
    resp.text = ""
    return resp


@override_settings(
    OPENAI_USE_PROXY=True,
    OPENAI_PROXY_BASE_URL="http://proxy.local:8080",
    OPENAI_PROXY_API_KEY="internal-secret",
    OPENAI_PROXY_TIMEOUT=30,
    PRODUCT_IMAGE_STYLE_PROMPT="studio photo",
    PRODUCT_IMAGE_MODEL="gpt-image-1",
    PRODUCT_IMAGE_OUTPUT_SIZE="1024x1024",
)
class ProxyModeTests(SimpleTestCase):
    """Поведение, когда OPENAI_USE_PROXY=True."""

    def test_calls_proxy_with_expected_payload(self):
        with patch(
            "apps.main.services.image_processor.requests.post",
            return_value=_ok_response(),
        ) as mock_post:
            result = process_product_image(b"raw-bytes", filename="p.jpg", mime_type="image/jpeg")

        self.assertEqual(result, b"PROCESSED_PNG_BYTES")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        # URL — точный путь /v1/images/edit без двойного слеша.
        self.assertEqual(args[0], "http://proxy.local:8080/v1/images/edit")
        # Заголовок передаётся.
        self.assertEqual(kwargs["headers"]["X-Internal-Api-Key"], "internal-secret")
        # multipart содержит изображение и текстовые поля.
        self.assertIn("image", kwargs["files"])
        self.assertEqual(kwargs["files"]["image"][0], "p.jpg")
        self.assertEqual(kwargs["files"]["image"][1], b"raw-bytes")
        self.assertEqual(kwargs["files"]["image"][2], "image/jpeg")
        self.assertEqual(kwargs["data"]["prompt"], "studio photo")
        self.assertEqual(kwargs["data"]["model"], "gpt-image-1")
        self.assertEqual(kwargs["data"]["size"], "1024x1024")
        self.assertEqual(kwargs["timeout"], 30.0)

    def test_proxy_unreachable_raises(self):
        with patch(
            "apps.main.services.image_processor.requests.post",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            with self.assertRaises(ImageProcessingError) as ctx:
                process_product_image(b"raw")
        self.assertIn("Proxy недоступен", str(ctx.exception))

    def test_proxy_timeout_raises(self):
        with patch(
            "apps.main.services.image_processor.requests.post",
            side_effect=requests.exceptions.Timeout("slow"),
        ):
            with self.assertRaises(ImageProcessingError) as ctx:
                process_product_image(b"raw")
        self.assertIn("Таймаут", str(ctx.exception))

    def test_proxy_returns_non_200_raises(self):
        bad = MagicMock()
        bad.status_code = 502
        bad.headers = {"Content-Type": "application/json"}
        bad.text = '{"detail":"OpenAI request failed"}'
        bad.content = bad.text.encode()
        with patch(
            "apps.main.services.image_processor.requests.post",
            return_value=bad,
        ):
            with self.assertRaises(ImageProcessingError) as ctx:
                process_product_image(b"raw")
        self.assertIn("502", str(ctx.exception))

    def test_proxy_returns_non_image_raises(self):
        bad = MagicMock()
        bad.status_code = 200
        bad.headers = {"Content-Type": "application/json"}
        bad.text = '{"unexpected":true}'
        bad.content = bad.text.encode()
        with patch(
            "apps.main.services.image_processor.requests.post",
            return_value=bad,
        ):
            with self.assertRaises(ImageProcessingError):
                process_product_image(b"raw")

    def test_proxy_empty_body_raises(self):
        empty = MagicMock()
        empty.status_code = 200
        empty.headers = {"Content-Type": "image/png"}
        empty.content = b""
        empty.text = ""
        with patch(
            "apps.main.services.image_processor.requests.post",
            return_value=empty,
        ):
            with self.assertRaises(ImageProcessingError):
                process_product_image(b"raw")

    def test_empty_image_short_circuits_before_network(self):
        """Пустой image_bytes даже не доходит до proxy."""

        with patch("apps.main.services.image_processor.requests.post") as mock_post:
            with self.assertRaises(ImageProcessingError):
                process_product_image(b"")
        mock_post.assert_not_called()


@override_settings(
    OPENAI_USE_PROXY=True,
    OPENAI_PROXY_BASE_URL="",
    OPENAI_PROXY_API_KEY="x",
    PRODUCT_IMAGE_STYLE_PROMPT="studio photo",
)
class ProxyMisconfiguredBaseUrlTests(SimpleTestCase):
    def test_missing_base_url_raises(self):
        with self.assertRaises(ImageProcessingError) as ctx:
            process_product_image(b"raw")
        self.assertIn("OPENAI_PROXY_BASE_URL", str(ctx.exception))


@override_settings(
    OPENAI_USE_PROXY=True,
    OPENAI_PROXY_BASE_URL="http://proxy.local:8080",
    OPENAI_PROXY_API_KEY="",
    PRODUCT_IMAGE_STYLE_PROMPT="studio photo",
)
class ProxyMisconfiguredKeyTests(SimpleTestCase):
    def test_missing_internal_key_raises(self):
        with self.assertRaises(ImageProcessingError) as ctx:
            process_product_image(b"raw")
        self.assertIn("OPENAI_PROXY_API_KEY", str(ctx.exception))


@override_settings(
    OPENAI_USE_PROXY=False,
    OPENAI_API_KEY="test-openai-key",
    PRODUCT_IMAGE_STYLE_PROMPT="studio photo",
    PRODUCT_IMAGE_MODEL="gpt-image-1",
    PRODUCT_IMAGE_OUTPUT_SIZE="1024x1024",
)
class DirectModeStillWorksTests(SimpleTestCase):
    """Регрессия: поведение по умолчанию не сломано."""

    def test_default_uses_openai_sdk_not_requests(self):
        # Если случайно зайдём в proxy-ветку — requests.post будет вызван,
        # это проверяется ассертом.
        fake_response = MagicMock()
        fake_response.data = [MagicMock(b64_json="aGVsbG8=")]  # base64("hello")
        fake_client = MagicMock()
        fake_client.images.edit.return_value = fake_response

        with patch(
            "apps.main.services.image_processor._get_client",
            return_value=fake_client,
        ), patch(
            "apps.main.services.image_processor.requests.post"
        ) as mock_post:
            result = process_product_image(b"raw")

        self.assertEqual(result, b"hello")
        mock_post.assert_not_called()
        fake_client.images.edit.assert_called_once()
