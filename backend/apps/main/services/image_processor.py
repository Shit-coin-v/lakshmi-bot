"""Сервис обработки фото товаров через OpenAI Image API.

Принимает байты исходной фотографии и возвращает байты обработанного
изображения в едином e-commerce-стиле. Сама RAW-копия не сохраняется
ни на диск, ни в логи: исходник существует только в памяти процесса
во время вызова и поднимается напрямую в OpenAI.

Все настройки берутся из ``django.conf.settings``:

- ``OPENAI_API_KEY`` — ключ API (обязателен).
- ``PRODUCT_IMAGE_STYLE_PROMPT`` — единый prompt стилизации.
- ``PRODUCT_IMAGE_MODEL`` — модель Image API (по умолчанию ``gpt-image-1``).
- ``PRODUCT_IMAGE_OUTPUT_SIZE`` — размер итогового файла (например ``1024x1024``).
- ``PRODUCT_IMAGE_PROCESSING_TIMEOUT`` — таймаут запроса к OpenAI в секундах.
"""

from __future__ import annotations

import base64
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class ImageProcessingError(Exception):
    """Ошибка обработки изображения через внешний API.

    Бросается, когда OpenAI недоступен, вернул некорректный ответ или
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


def process_product_image(
    image_bytes: bytes,
    *,
    mime_type: str = "image/png",
    filename: str = "photo.png",
) -> bytes:
    """Прогнать исходное фото через OpenAI Image API.

    Использует ``images.edit`` с фиксированным prompt-ом из настроек, чтобы
    привести все фото товаров к единому стилю каталога.

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
    model = getattr(settings, "PRODUCT_IMAGE_MODEL", "gpt-image-1")

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


__all__ = ["ImageProcessingError", "process_product_image"]
