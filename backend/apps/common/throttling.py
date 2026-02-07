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
