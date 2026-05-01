"""Утилиты для маскирования чувствительных данных в логах.

Используются при логировании FCM-токенов, newsletter-токенов и любых
secret-like значений: вместо полного значения в лог уходит короткий хеш,
по которому невозможно восстановить токен, но можно сопоставить разные
вхождения одного и того же значения между логами.

Также содержит logging.Filter, скрывающий из traceback'ов значения
переменных, чьи имена матчат secret-like паттернам.
"""
from __future__ import annotations

import hashlib
import logging
import re

# Имена переменных, чьи значения нельзя печатать в логах (включая трейсбэки).
_SECRET_NAME_RE = re.compile(
    r"(?i)(?:secret|password|passwd|pwd|token|api[_-]?key|authorization|"
    r"bearer|cookie|session|csrf|x-api-key|firebase|bot_token)"
)


def mask_token(value: str | None, *, prefix: int = 6, suffix: int = 4) -> str:
    """Заменить токен на «префикс…суффикс#хеш».

    Пример: ``"1234567890abcdef…WXYZ#a1b2c3d4"``.
    SHA-256 первых 8 hex-символов — устойчиво к коллизиям при сопоставлении
    одного токена в разных строках лога, но не позволяет восстановить значение.
    """
    if not value:
        return "<empty>"
    if len(value) <= prefix + suffix:
        # Слишком короткий — печатаем только хеш, чтобы не утечь полностью.
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
        return f"<short#{digest}>"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return f"{value[:prefix]}…{value[-suffix:]}#{digest}"


def mask_email(value: str | None) -> str:
    """Замаскировать email для логов: ``a***a@example.com``.

    Сохраняет домен (нужен для дебага «не работает почта на gmail.com»),
    но скрывает локальную часть. Если строка не похожа на email —
    возвращаем ``<masked>``.
    """
    if not value:
        return "<empty>"
    if "@" not in value:
        return "<masked>"
    local, _, domain = value.rpartition("@")
    if not local:
        return f"<empty>@{domain}"
    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = f"{local[0]}***{local[-1]}"
    return f"{masked_local}@{domain}"


def mask_phone(value: str | None) -> str:
    """Замаскировать телефон, оставив только последние 4 цифры: ``+7******1234``.

    Не парсит формат E.164 — просто маскирует все цифры кроме хвоста.
    """
    if not value:
        return "<empty>"
    digits = [c for c in value if c.isdigit()]
    if len(digits) <= 4:
        return "<short>"
    tail = "".join(digits[-4:])
    return f"***{tail}"


class RedactSecretsFilter(logging.Filter):
    """logging.Filter, заменяющий значения secret-like ключей на ``***``.

    Пробегает по message и args, ищет паттерны ``KEY=VALUE`` или ``KEY: VALUE``.
    Не панацея — но снимает основной класс утечек через format-строки и
    serialised dict в логах.
    """

    _PAIR_RE = re.compile(
        r"(?P<k>[A-Za-z][A-Za-z0-9_\-]*)\s*[:=]\s*"
        r"(?P<q>['\"]?)(?P<v>[^'\"\s,;}]+)(?P=q)"
    )

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        redacted = self._redact(msg)
        if redacted != msg:
            # Подменяем сообщение целиком, args обнуляем — мы уже отрендерили.
            record.msg = redacted
            record.args = None
        return True

    @classmethod
    def _redact(cls, text: str) -> str:
        def _sub(m: re.Match) -> str:
            key = m.group("k")
            if _SECRET_NAME_RE.search(key):
                return f"{key}={m.group('q')}***{m.group('q')}"
            return m.group(0)

        return cls._PAIR_RE.sub(_sub, text)
