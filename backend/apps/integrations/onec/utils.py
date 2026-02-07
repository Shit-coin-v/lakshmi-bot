"""Shared utilities for 1C integration endpoints."""
from __future__ import annotations

from typing import Any

from django.http import JsonResponse


def onec_error(
    error_code: str,
    message: str,
    *,
    details: Any | None = None,
    status_code: int = 400,
):
    payload: dict[str, Any] = {"error_code": error_code, "message": message}
    if details is not None:
        payload["details"] = details
    return JsonResponse(payload, status=status_code)
