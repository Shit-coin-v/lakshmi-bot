"""Security helpers for the 1C integration endpoints."""

import logging
import os
from functools import wraps
from hmac import compare_digest
from typing import Iterable

from django.http import JsonResponse

logger = logging.getLogger(__name__)

API_KEY = (os.getenv("INTEGRATION_API_KEY") or "").strip()


def _get_onec_api_key() -> str:
    """Lazy read ONEC_API_KEY from settings (available after Django setup)."""
    from django.conf import settings as django_settings

    return getattr(django_settings, "ONEC_API_KEY", "") or ""


_ALLOWED_IPS: tuple[str, ...] = tuple(
    ip.strip() for ip in (os.getenv("ONEC_ALLOW_IPS") or "").split(",") if ip.strip()
)


def _client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        # Last IP — appended by nginx ($proxy_add_x_forwarded_for).
        # First one can be spoofed by client.
        return xff.split(",")[-1].strip()
    xri = request.META.get("HTTP_X_REAL_IP")
    if xri:
        return xri.strip()
    return request.META.get("REMOTE_ADDR", "")


def _iter_ip_rules() -> Iterable[str]:
    if not _ALLOWED_IPS:
        return ()
    return _ALLOWED_IPS


def _ip_allowed(request) -> bool:
    """Check client IP against whitelist. Empty whitelist denies in production."""

    rules = list(_iter_ip_rules())
    if not rules:
        from django.conf import settings as django_settings

        if not getattr(django_settings, "DEBUG", False):
            logger.error("ONEC AUTH: IP whitelist empty in production — denying")
            return False
        logger.warning("ONEC AUTH: IP whitelist empty (DEBUG), allowing all")
        return True

    real_ip = _client_ip(request)
    for allowed in rules:
        if allowed.endswith("*"):
            if real_ip.startswith(allowed[:-1]):
                return True
        elif real_ip == allowed:
            return True
    return False


def require_onec_auth(view_func):
    """Simple API key authentication with optional IP whitelisting."""

    def _bad(code, detail):
        return JsonResponse({"detail": detail}, status=code)

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        onec_key = _get_onec_api_key()
        if not onec_key:
            logger.error("ONEC AUTH denied: server auth not configured")
            return _bad(401, "Server auth not configured")

        if not _ip_allowed(request):
            logger.warning(
                "ONEC AUTH denied: ip not allowed ip=%s path=%s",
                _client_ip(request),
                getattr(request, "path", "?"),
            )
            return _bad(403, "IP not allowed")

        api_key = (
            getattr(request, "headers", {}).get("X-Api-Key")
            or request.META.get("HTTP_X_API_KEY")
            or ""
        ).strip()

        if not api_key:
            logger.warning(
                "ONEC AUTH denied: missing api key ip=%s path=%s",
                _client_ip(request),
                getattr(request, "path", "?"),
            )
            return _bad(401, "Missing API key")

        if not compare_digest(api_key, onec_key):
            logger.warning(
                "ONEC AUTH denied: bad api key ip=%s path=%s",
                _client_ip(request),
                getattr(request, "path", "?"),
            )
            return _bad(401, "Bad API key")

        return view_func(request, *args, **kwargs)

    return _wrapped


__all__ = ["API_KEY", "require_onec_auth"]
