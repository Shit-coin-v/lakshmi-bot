from __future__ import annotations

from hmac import compare_digest

from rest_framework.permissions import BasePermission

from .security import API_KEY


class ApiKeyPermission(BasePermission):
    """Simple X-Api-Key gatekeeper for selected endpoints."""

    message = "Missing or invalid API key"

    def has_permission(self, request, view):
        if not API_KEY:
            return False

        provided = (
            request.headers.get("X-Api-Key")
            or request.META.get("HTTP_X_API_KEY")
            or request.META.get("HTTP_X_ONEC_AUTH")
            or ""
        ).strip()
        return provided and compare_digest(provided, API_KEY)
