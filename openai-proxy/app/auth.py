"""Аутентификация запросов от Django backend по X-Internal-Api-Key."""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from .config import get_settings


async def require_internal_key(
    x_internal_api_key: str | None = Header(default=None, alias="X-Internal-Api-Key"),
) -> None:
    """Проверка X-Internal-Api-Key.

    Используем ``hmac.compare_digest`` для защиты от timing-атак.
    Если ключ не настроен на сервере — отвечаем 503: сервис не готов
    принимать запросы, но не утечка о том, что аутентификация выключена.
    """

    settings = get_settings()
    expected = (settings.internal_api_key or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Proxy is not configured",
        )

    provided = (x_internal_api_key or "").strip()
    if not provided or not hmac.compare_digest(expected, provided):
        # 401 — ключ отсутствует или неверный. В тело не кладём подсказок.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
