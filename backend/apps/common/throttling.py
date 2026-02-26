from rest_framework.throttling import SimpleRateThrottle


class TelegramUserThrottle(SimpleRateThrottle):
    """Rate-limit authenticated Telegram users by their user PK."""

    scope = "telegram_user"

    def get_cache_key(self, request, view):
        telegram_user = getattr(request, "telegram_user", None)
        if telegram_user is None:
            return None  # skip — AnonRateThrottle handles unauthenticated
        return self.cache_format % {
            "scope": self.scope,
            "ident": telegram_user.pk,
        }


class AnonAuthThrottle(SimpleRateThrottle):
    """Strict rate limit for auth endpoints (login, register, reset)."""

    scope = "anon_auth"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class VerifyCodeThrottle(SimpleRateThrottle):
    """Very strict limit for code verification (brute-force prevention)."""

    scope = "verify_code"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
