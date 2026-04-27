"""Тонкая обёртка над OpenAI Image API.

Изолирует прямой вызов SDK от FastAPI-handler, чтобы:
- удобно мокать в тестах;
- логика ретраев/тайм-аутов жила в одном месте;
- секрет (api_key) не утекал в стектрейсы handler'а.
"""

from __future__ import annotations

import base64
import logging

from .config import get_settings

logger = logging.getLogger(__name__)


class ProxyError(Exception):
    """Общая ошибка обработки на стороне proxy.

    Атрибут ``status_code`` подсказывает FastAPI handler'у, какой HTTP вернуть.
    """

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def _get_client():
    """Создать OpenAI-клиент с api_key и timeout из настроек.

    Импорт SDK ленивый: при пустом ``OPENAI_API_KEY`` или отсутствии
    пакета сразу отдаём осмысленную 503/500.
    """

    settings = get_settings()
    api_key = (settings.openai_api_key or "").strip()
    if not api_key:
        raise ProxyError("OPENAI_API_KEY is not configured", status_code=503)

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover — защитный гард
        raise ProxyError("openai SDK not installed", status_code=500) from exc

    return OpenAI(api_key=api_key, timeout=float(settings.openai_request_timeout))


def edit_image(
    image_bytes: bytes,
    *,
    prompt: str,
    model: str,
    size: str,
    mime_type: str = "image/png",
    filename: str = "photo.png",
) -> bytes:
    """Прогнать изображение через OpenAI Image Edit API и вернуть PNG-байты.

    :param image_bytes: байты исходного изображения.
    :param prompt: prompt стилизации; формирует Django backend.
    :param model: id модели, передаётся как есть в SDK.
    :param size: размер итогового файла, например ``1024x1024``.
    :param mime_type: MIME-тип входного файла.
    :param filename: имя файла для SDK (определяет формат).
    :raises ProxyError: при ошибке OpenAI или невалидном ответе.
    """

    if not image_bytes:
        raise ProxyError("Empty image", status_code=400)
    if not prompt:
        raise ProxyError("Empty prompt", status_code=400)
    if not model:
        raise ProxyError("Empty model", status_code=400)
    if not size:
        raise ProxyError("Empty size", status_code=400)

    client = _get_client()

    try:
        response = client.images.edit(
            model=model,
            image=(filename or "photo.png", image_bytes, mime_type or "image/png"),
            prompt=prompt,
            size=size,
            n=1,
        )
    except Exception as exc:
        # Логируем тип/repr ошибки SDK без тела запроса.
        # Важно: НЕ логировать prompt и сами байты изображения.
        logger.warning("OpenAI image edit failed: %s", type(exc).__name__)
        # Различаем таймаут и прочее: SDK кидает APITimeoutError.
        from openai import APITimeoutError  # ленивый импорт, чтобы не падать без SDK

        if isinstance(exc, APITimeoutError):
            raise ProxyError("OpenAI timeout", status_code=504) from exc
        raise ProxyError("OpenAI request failed", status_code=502) from exc

    data = getattr(response, "data", None) or []
    if not data:
        raise ProxyError("OpenAI returned empty response", status_code=502)

    b64 = getattr(data[0], "b64_json", None)
    if not b64:
        raise ProxyError("OpenAI did not return image", status_code=502)

    try:
        return base64.b64decode(b64)
    except (TypeError, ValueError) as exc:
        raise ProxyError("Invalid base64 in OpenAI response", status_code=502) from exc


__all__ = ["ProxyError", "edit_image"]
