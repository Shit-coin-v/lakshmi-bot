from __future__ import annotations

from hmac import compare_digest

from rest_framework.permissions import BasePermission

from .security import API_KEY


class ApiKeyPermission(BasePermission):
    """Simple X-Api-Key gatekeeper for selected endpoints."""

    message = "Missing or invalid API key"

    def _get_api_key(self):
        """Return the configured API key, checking settings first for testability."""
        from django.conf import settings as django_settings

        key = getattr(django_settings, "INTEGRATION_API_KEY", "") or ""
        return key.strip() or API_KEY

    def has_permission(self, request, view):
        api_key = self._get_api_key()
        if not api_key:
            return False

        provided = (
            request.headers.get("X-Api-Key")
            or request.META.get("HTTP_X_API_KEY")
            or request.META.get("HTTP_X_ONEC_AUTH")
            or ""
        ).strip()
        return provided and compare_digest(provided, api_key)


class TelegramUserPermission(BasePermission):
    """Check X-Telegram-User-Id header and attach user to request.

    Deprecated: use CustomerPermission instead.
    """

    message = "Missing or invalid Telegram user ID"

    def has_permission(self, request, view):
        from apps.main.models import CustomUser

        header = (
            request.headers.get("X-Telegram-User-Id")
            or request.META.get("HTTP_X_TELEGRAM_USER_ID")
            or ""
        ).strip()
        if not header:
            return False

        try:
            telegram_id = int(header)
        except (ValueError, TypeError):
            return False

        try:
            request.telegram_user = CustomUser.objects.get(telegram_id=telegram_id)
        except CustomUser.DoesNotExist:
            return False

        return True


class CustomerPermission(BasePermission):
    """Unified customer auth: JWT Bearer token OR X-Telegram-User-Id header.

    Sets ``request.telegram_user`` to the authenticated CustomUser instance
    (attribute name kept for backward compatibility).
    """

    message = "Authentication required"

    def has_permission(self, request, view):
        from apps.main.models import CustomUser

        # 1. Try JWT Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token:
                from .authentication import decode_token

                user_id = decode_token(token, expected_type="access")
                if user_id is not None:
                    try:
                        request.telegram_user = CustomUser.objects.get(pk=user_id)
                        return True
                    except CustomUser.DoesNotExist:
                        return False
                # Token present but invalid/expired — return False.
                # Frontend interceptor catches 403 when Bearer was sent
                # and triggers token refresh.
                return False

        # 2. Fallback: X-Telegram-User-Id header (behind feature flag)
        from django.conf import settings as django_settings

        if not getattr(django_settings, "ALLOW_TELEGRAM_HEADER_AUTH", False):
            return False

        header = (
            request.headers.get("X-Telegram-User-Id")
            or request.META.get("HTTP_X_TELEGRAM_USER_ID")
            or ""
        ).strip()
        if not header:
            return False

        try:
            telegram_id = int(header)
        except (ValueError, TypeError):
            return False

        try:
            request.telegram_user = CustomUser.objects.get(telegram_id=telegram_id)
        except CustomUser.DoesNotExist:
            return False

        return True
