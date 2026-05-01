"""Email verification and password reset code service."""

import hmac
import logging
import secrets
import string

from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings

from shared.log_redact import mask_email

logger = logging.getLogger(__name__)

CODE_LENGTH = 6
CODE_TTL = 600  # 10 minutes


def _generate_code() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(CODE_LENGTH))


def _cache_key(prefix: str, email: str) -> str:
    return f"{prefix}:{email.lower().strip()}"


def send_verification_code(email: str) -> str:
    """Generate and send an email verification code. Returns the code."""
    code = _generate_code()
    cache.set(_cache_key("email_verify", email), code, timeout=CODE_TTL)
    send_mail(
        subject="Код подтверждения",
        message=f"Ваш код подтверждения: {code}\nКод действителен 10 минут.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
    logger.info("Verification code sent to %s", mask_email(email))
    return code


def verify_code(email: str, code: str) -> bool:
    """Check the verification code. Deletes it on success."""
    key = _cache_key("email_verify", email)
    stored = cache.get(key)
    if stored is not None and hmac.compare_digest(stored, code):
        cache.delete(key)
        return True
    return False


def send_reset_code(email: str) -> str:
    """Generate and send a password reset code. Returns the code."""
    code = _generate_code()
    cache.set(_cache_key("pwd_reset", email), code, timeout=CODE_TTL)
    send_mail(
        subject="Сброс пароля",
        message=f"Код для сброса пароля: {code}\nКод действителен 10 минут.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
    logger.info("Password reset code sent to %s", mask_email(email))
    return code


def verify_reset_code(email: str, code: str) -> bool:
    """Check the password reset code. Deletes it on success."""
    key = _cache_key("pwd_reset", email)
    stored = cache.get(key)
    if stored is not None and hmac.compare_digest(stored, code):
        cache.delete(key)
        return True
    return False


def send_link_code(user_id: int) -> str:
    """Generate a code for linking Telegram account. Returns the code."""
    code = _generate_code()
    cache.set(f"link_telegram:{code}", user_id, timeout=CODE_TTL)
    logger.info("Telegram link code generated for user_id=%s", user_id)
    return code


def verify_link_code(code: str) -> int | None:
    """Check the Telegram link code. Returns user_id or None. Deletes on success."""
    key = f"link_telegram:{code}"
    user_id = cache.get(key)
    if user_id is not None:
        cache.delete(key)
        return user_id
    return None
