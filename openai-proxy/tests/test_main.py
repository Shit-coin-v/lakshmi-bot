"""Тесты openai-proxy.

Цель — проверить контракт endpoint без реального вызова OpenAI:
- /health не требует аутентификации;
- /v1/images/edit без ключа → 401;
- с правильным ключом и валидным multipart → 200 + image/png;
- слишком большой файл → 413;
- ошибка OpenAI → 502; таймаут → 504.

OpenAI SDK мокается: подменяем функцию edit_image из app.openai_client.
"""

from __future__ import annotations

import io
from unittest.mock import patch


def _png_bytes() -> bytes:
    """Минимальный PNG: 1x1 прозрачный пиксель."""

    # Готовая последовательность валидных PNG-байтов.
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00"
        b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _multipart(image_bytes: bytes):
    return {
        "image": ("photo.png", io.BytesIO(image_bytes), "image/png"),
    }


def _form_data():
    return {
        "prompt": "studio product photo",
        "model": "gpt-image-1",
        "size": "1024x1024",
    }


def test_health_no_auth(client):
    """/health доступен без ключа."""

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_images_edit_without_key_returns_401(client):
    resp = client.post(
        "/v1/images/edit",
        files=_multipart(_png_bytes()),
        data=_form_data(),
    )
    assert resp.status_code == 401


def test_images_edit_with_wrong_key_returns_401(client):
    resp = client.post(
        "/v1/images/edit",
        headers={"X-Internal-Api-Key": "wrong"},
        files=_multipart(_png_bytes()),
        data=_form_data(),
    )
    assert resp.status_code == 401


def test_images_edit_happy_path(client):
    """С правильным ключом и валидным запросом возвращаем PNG."""

    processed = b"PROCESSED_IMAGE_BYTES"
    with patch("app.main.edit_image", return_value=processed) as mock_edit:
        resp = client.post(
            "/v1/images/edit",
            headers={"X-Internal-Api-Key": "test-internal-key"},
            files=_multipart(_png_bytes()),
            data=_form_data(),
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content == processed

    # Проверяем, что в edit_image передались поля, не дефолты.
    kwargs = mock_edit.call_args.kwargs
    assert kwargs["prompt"] == "studio product photo"
    assert kwargs["model"] == "gpt-image-1"
    assert kwargs["size"] == "1024x1024"


def test_images_edit_empty_image_returns_400(client):
    resp = client.post(
        "/v1/images/edit",
        headers={"X-Internal-Api-Key": "test-internal-key"},
        files={"image": ("photo.png", io.BytesIO(b""), "image/png")},
        data=_form_data(),
    )
    assert resp.status_code == 400


def test_images_edit_too_large_returns_413(client, monkeypatch):
    """MAX_IMAGE_SIZE_BYTES=1048576 (1 МБ) — отправляем 2 МБ."""

    big = b"\x00" * (2 * 1024 * 1024)
    resp = client.post(
        "/v1/images/edit",
        headers={"X-Internal-Api-Key": "test-internal-key"},
        files={"image": ("big.png", io.BytesIO(big), "image/png")},
        data=_form_data(),
    )
    assert resp.status_code == 413


def test_images_edit_openai_error_returns_502(client):
    from app.openai_client import ProxyError

    def boom(*_, **__):
        raise ProxyError("OpenAI request failed", status_code=502)

    with patch("app.main.edit_image", side_effect=boom):
        resp = client.post(
            "/v1/images/edit",
            headers={"X-Internal-Api-Key": "test-internal-key"},
            files=_multipart(_png_bytes()),
            data=_form_data(),
        )
    assert resp.status_code == 502


def test_images_edit_timeout_returns_504(client):
    from app.openai_client import ProxyError

    def slow(*_, **__):
        raise ProxyError("OpenAI timeout", status_code=504)

    with patch("app.main.edit_image", side_effect=slow):
        resp = client.post(
            "/v1/images/edit",
            headers={"X-Internal-Api-Key": "test-internal-key"},
            files=_multipart(_png_bytes()),
            data=_form_data(),
        )
    assert resp.status_code == 504


def test_no_internal_key_configured_returns_503(monkeypatch):
    """Если INTERNAL_API_KEY не настроен — proxy отвечает 503, не 401."""

    monkeypatch.setenv("OPENAI_API_KEY", "test")
    # INTERNAL_API_KEY НЕ ставим.
    from app import config

    config._settings = None
    import sys

    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    from fastapi.testclient import TestClient

    from app.main import app

    test_client = TestClient(app)

    resp = test_client.post(
        "/v1/images/edit",
        headers={"X-Internal-Api-Key": "anything"},
        files=_multipart(_png_bytes()),
        data=_form_data(),
    )
    assert resp.status_code == 503
    config._settings = None
