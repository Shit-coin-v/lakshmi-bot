"""Сервис обработки фото товаров через OpenAI Image API.

Принимает байты исходной фотографии и возвращает байты обработанного
изображения в едином e-commerce-стиле. Сама RAW-копия не сохраняется
ни на диск, ни в логи: исходник существует только в памяти процесса
во время вызова и поднимается напрямую в OpenAI (или в openai-proxy).

Все настройки берутся из ``django.conf.settings``:

- ``OPENAI_API_KEY`` — ключ API (обязателен в direct-режиме).
- ``PRODUCT_IMAGE_STYLE_PROMPT`` — единый prompt стилизации.
- ``PRODUCT_IMAGE_MODEL`` — модель Image API (по умолчанию ``gpt-image-2``).
- ``PRODUCT_IMAGE_OUTPUT_SIZE`` — размер итогового файла (например ``1024x1024``).
- ``PRODUCT_IMAGE_PROCESSING_TIMEOUT`` — таймаут запроса к OpenAI в секундах.

Режим прокси (включается ``OPENAI_USE_PROXY=True``):

- ``OPENAI_PROXY_BASE_URL`` — адрес внутреннего сервиса (например ``http://10.0.0.5:8080``).
- ``OPENAI_PROXY_API_KEY`` — внутренний ключ, передаётся как ``X-Internal-Api-Key``.
- ``OPENAI_PROXY_TIMEOUT`` — таймаут HTTP-запроса к proxy, секунды.

В режиме прокси ``OPENAI_API_KEY`` на этом сервере не нужен — ключ
хранится только на стороне proxy.
"""

from __future__ import annotations

import base64
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ImageProcessingError(Exception):
    """Ошибка обработки изображения через внешний API.

    Бросается, когда OpenAI/proxy недоступен, вернул некорректный ответ или
    конфигурация неполная. View конвертирует это в 502/400 для клиента.
    """


def _get_client():
    """Создать ленивый OpenAI-клиент.

    Импорт пакета ``openai`` сделан внутри функции, чтобы:
    - тесты могли заменять ``process_product_image`` без установки SDK;
    - отсутствие ``OPENAI_API_KEY`` бросало понятный ``ImageProcessingError``,
      а не ImportError на старте.
    """

    api_key = (getattr(settings, "OPENAI_API_KEY", "") or "").strip()
    if not api_key:
        raise ImageProcessingError("OPENAI_API_KEY не настроен")

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover — защитный гард
        raise ImageProcessingError("Пакет openai не установлен") from exc

    timeout = float(getattr(settings, "PRODUCT_IMAGE_PROCESSING_TIMEOUT", 120))
    return OpenAI(api_key=api_key, timeout=timeout)


def _call_openai_direct(
    image_bytes: bytes,
    *,
    prompt: str,
    model: str,
    size: str,
    mime_type: str,
    filename: str,
) -> bytes:
    """Прямой вызов OpenAI Image Edit (текущий режим, default)."""

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
        # Ловим всё, что выбрасывает OpenAI SDK — таймауты, сетевые ошибки,
        # 4xx/5xx. Сообщение исключения OpenAI безопасно для лога,
        # секреты SDK не печатает.
        logger.exception("OpenAI image edit failed")
        raise ImageProcessingError(f"Ошибка обработки фото: {exc}") from exc

    data = getattr(response, "data", None) or []
    if not data:
        raise ImageProcessingError("OpenAI вернул пустой ответ")

    b64 = getattr(data[0], "b64_json", None)
    if not b64:
        raise ImageProcessingError("OpenAI не вернул изображение")

    try:
        return base64.b64decode(b64)
    except (TypeError, ValueError) as exc:
        raise ImageProcessingError("Не удалось декодировать ответ OpenAI") from exc


def _call_via_proxy(
    image_bytes: bytes,
    *,
    prompt: str,
    model: str,
    size: str,
    mime_type: str,
    filename: str,
) -> bytes:
    """Вызов через внутренний openai-proxy (внешний VPS).

    Контракт proxy: POST {base_url}/v1/images/edit, multipart с полями
    image/prompt/model/size; заголовок X-Internal-Api-Key. Ответ при успехе —
    Content-Type: image/png, тело — байты PNG.
    """

    base_url = (getattr(settings, "OPENAI_PROXY_BASE_URL", "") or "").rstrip("/")
    if not base_url:
        raise ImageProcessingError("OPENAI_PROXY_BASE_URL не настроен")

    internal_key = (getattr(settings, "OPENAI_PROXY_API_KEY", "") or "").strip()
    if not internal_key:
        raise ImageProcessingError("OPENAI_PROXY_API_KEY не настроен")

    timeout = float(getattr(settings, "OPENAI_PROXY_TIMEOUT", 120))

    files = {
        "image": (filename or "photo.png", image_bytes, mime_type or "image/png"),
    }
    data = {"prompt": prompt, "model": model, "size": size}
    headers = {"X-Internal-Api-Key": internal_key}

    try:
        resp = requests.post(
            f"{base_url}/v1/images/edit",
            files=files,
            data=data,
            headers=headers,
            timeout=timeout,
        )
    except requests.exceptions.Timeout as exc:
        logger.warning("openai-proxy timeout after %.1fs", timeout)
        raise ImageProcessingError("Таймаут обращения к proxy") from exc
    except requests.exceptions.ConnectionError as exc:
        logger.warning("openai-proxy unreachable: %s", type(exc).__name__)
        raise ImageProcessingError("Proxy недоступен") from exc
    except requests.exceptions.RequestException as exc:
        logger.warning("openai-proxy request failed: %s", type(exc).__name__)
        raise ImageProcessingError(f"Ошибка обращения к proxy: {exc}") from exc

    if resp.status_code != 200:
        # Логируем только статус и короткий хвост тела (без секретов).
        # В body proxy не кладёт ни prompt, ни картинку.
        body_preview = (resp.text or "")[:200].replace("\n", " ")
        logger.warning(
            "openai-proxy returned %s: %s", resp.status_code, body_preview
        )
        raise ImageProcessingError(
            f"Proxy вернул ошибку {resp.status_code}"
        )

    content_type = (resp.headers.get("Content-Type") or "").lower()
    if "image/" not in content_type:
        raise ImageProcessingError("Proxy вернул не изображение")

    if not resp.content:
        raise ImageProcessingError("Proxy вернул пустой ответ")

    return resp.content


def process_product_image(
    image_bytes: bytes,
    *,
    mime_type: str = "image/png",
    filename: str = "photo.png",
) -> bytes:
    """Прогнать исходное фото через OpenAI Image API (или proxy).

    По умолчанию вызывает OpenAI напрямую. Если включён proxy-режим
    (``settings.OPENAI_USE_PROXY=True``), обращение идёт через внутренний
    сервис ``openai-proxy``.

    :param image_bytes: байты исходного изображения.
    :param mime_type: MIME-тип входного файла (``image/jpeg``/``image/png`` и т.п.).
    :param filename: оригинальное имя файла — нужно OpenAI SDK для определения формата.
    :return: байты обработанного PNG.
    :raises ImageProcessingError: при сбое сети, таймауте, ошибке API или
        некорректном ответе. View не должен сохранять фото при этом исключении.
    """

    if not image_bytes:
        raise ImageProcessingError("Пустое изображение")

    prompt = (getattr(settings, "PRODUCT_IMAGE_STYLE_PROMPT", "") or "").strip()
    if not prompt:
        raise ImageProcessingError("PRODUCT_IMAGE_STYLE_PROMPT не настроен")

    size = getattr(settings, "PRODUCT_IMAGE_OUTPUT_SIZE", "1024x1024")
    model = getattr(settings, "PRODUCT_IMAGE_MODEL", "gpt-image-2")

    if getattr(settings, "OPENAI_USE_PROXY", False):
        return _call_via_proxy(
            image_bytes,
            prompt=prompt,
            model=model,
            size=size,
            mime_type=mime_type,
            filename=filename,
        )

    return _call_openai_direct(
        image_bytes,
        prompt=prompt,
        model=model,
        size=size,
        mime_type=mime_type,
        filename=filename,
    )


__all__ = ["ImageProcessingError", "process_product_image"]
