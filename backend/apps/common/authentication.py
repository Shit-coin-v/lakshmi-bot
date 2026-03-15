"""JWT token helpers and DRF authentication class."""

import datetime
import logging

import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)

_ALGORITHM = "HS256"
ACCESS_TOKEN_LIFETIME = datetime.timedelta(minutes=30)
REFRESH_TOKEN_LIFETIME = datetime.timedelta(days=7)


def _secret():
    return settings.SECRET_KEY


def generate_tokens(user) -> dict:
    """Return {"access": ..., "refresh": ...} for the given CustomUser."""
    now = datetime.datetime.now(datetime.timezone.utc)
    access_payload = {
        "user_id": user.pk,
        "type": "access",
        "iat": now,
        "exp": now + ACCESS_TOKEN_LIFETIME,
    }
    refresh_payload = {
        "user_id": user.pk,
        "type": "refresh",
        "iat": now,
        "exp": now + REFRESH_TOKEN_LIFETIME,
    }
    return {
        "access": jwt.encode(access_payload, _secret(), algorithm=_ALGORITHM),
        "refresh": jwt.encode(refresh_payload, _secret(), algorithm=_ALGORITHM),
    }


def decode_token(token: str, expected_type: str = "access") -> int | None:
    """Decode a JWT and return the user_id, or None on failure."""
    try:
        payload = jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

    if payload.get("type") != expected_type:
        return None

    return payload.get("user_id")


class JWTAuthentication(BaseAuthentication):
    """Optional JWT authentication for views with AllowAny.

    - No Authorization header → returns None (anonymous request).
    - Non-Bearer Authorization header → returns None (let other auth handle it).
    - Bearer token present but invalid/expired → raises AuthenticationFailed (401).
    - Valid Bearer token → returns (CustomUser, token).
    """

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:].strip()
        if not token:
            return None

        user_id = decode_token(token, expected_type="access")
        if user_id is None:
            raise AuthenticationFailed("Invalid or expired token.")

        from apps.main.models import CustomUser

        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            raise AuthenticationFailed("User not found.")

        return (user, token)

    def authenticate_header(self, request):
        return "Bearer"
