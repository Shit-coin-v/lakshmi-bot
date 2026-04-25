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


class ProductImageUploadThrottle(SimpleRateThrottle):
    """Лимит загрузки фото товара через X-Api-Key.

    Используется в Lakshmi Photo Studio: приложение сотрудника шлёт фото
    в OpenAI, и без лимита можно случайно сжечь квоту. Идентификация по
    значению заголовка X-Api-Key, а не по IP, потому что приложение
    обычно ходит из одной офисной сети.
    """

    scope = "product_image_upload"

    def get_cache_key(self, request, view):
        provided = (
            request.headers.get("X-Api-Key")
            or request.META.get("HTTP_X_API_KEY")
            or ""
        ).strip()
        if not provided:
            # Без ключа throttle пропускает запрос — его всё равно
            # отвергнет ApiKeyPermission с 403.
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": provided,
        }
