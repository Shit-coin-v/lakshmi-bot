"""FastAPI приложение openai-proxy.

Endpoints:
- GET  /health           — liveness/readiness, без аутентификации.
- POST /v1/images/edit   — прокси к OpenAI Image Edit, требует X-Internal-Api-Key.

Контракт /v1/images/edit:
- multipart/form-data
  - image:  файл (обязателен)
  - prompt: строка
  - model:  строка
  - size:   строка (например "1024x1024")
- 200 → Content-Type: image/png, тело — байты обработанного PNG.
- 401 — нет/неверный X-Internal-Api-Key
- 400 — отсутствуют/пустые поля
- 413 — файл больше MAX_IMAGE_SIZE_BYTES
- 502 — OpenAI вернул ошибку или невалидный ответ
- 503 — proxy не настроен (нет OPENAI_API_KEY/INTERNAL_API_KEY)
- 504 — таймаут OpenAI

Не логирует: байты изображения, prompt, ключи.
"""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, File, Form, HTTPException, Response, UploadFile, status

from .auth import require_internal_key
from .config import get_settings
from .openai_client import ProxyError, edit_image


def _configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, (settings.log_level or "INFO").upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


_configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="lakshmi openai-proxy", version="1.0.0")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness/readiness. Не требует аутентификации.

    Пробрасывается для healthcheck Docker и наблюдаемости. Не возвращает
    никаких настроек или версий компонентов, чтобы не светить детали наружу.
    """

    return {"status": "ok"}


@app.post(
    "/v1/images/edit",
    dependencies=[Depends(require_internal_key)],
    response_class=Response,
)
async def images_edit(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    model: str = Form(...),
    size: str = Form(...),
) -> Response:
    """Принять multipart-запрос от Django backend, вызвать OpenAI, вернуть PNG."""

    settings = get_settings()

    if not image:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty image")

    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty image")

    if len(raw) > int(settings.max_image_size_bytes):
        # 413 — отдельно от 400, чтобы upstream мог человеко-читаемо сообщить
        # в photo-studio про размер файла.
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large",
        )

    try:
        png_bytes = edit_image(
            raw,
            prompt=prompt,
            model=model,
            size=size,
            mime_type=image.content_type or "image/png",
            filename=image.filename or "photo",
        )
    except ProxyError as exc:
        # Логируем status_code и тип ошибки, но не prompt/байты/ключи.
        logger.warning(
            "images_edit failed status=%s type=%s",
            exc.status_code,
            type(exc.__cause__).__name__ if exc.__cause__ else "ProxyError",
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return Response(content=png_bytes, media_type="image/png", status_code=status.HTTP_200_OK)
