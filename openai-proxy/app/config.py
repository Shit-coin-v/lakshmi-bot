"""Настройки openai-proxy.

Все значения читаются из переменных окружения через pydantic-settings.
Реальные значения держим в .env (не коммитится). Шаблон — в .env.example.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация сервиса.

    - openai_api_key — ключ OpenAI, обязателен.
    - internal_api_key — внутренний ключ от Django backend, обязателен.
    - openai_request_timeout — секунды; должно быть <= таймаута upstream.
    - max_image_size_bytes — защита от загрузки гигантских файлов.
    - log_level — уровень логирования.
    - proxy_port — порт uvicorn внутри контейнера.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    openai_api_key: str = Field(default="")
    internal_api_key: str = Field(default="")
    openai_request_timeout: float = 120.0
    max_image_size_bytes: int = 10 * 1024 * 1024
    log_level: str = "INFO"
    proxy_port: int = 8080


_settings: Settings | None = None


def get_settings() -> Settings:
    """Singleton-доступ к настройкам.

    FastAPI Depends() вызывает её на каждый запрос, поэтому кэшируем.
    """

    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
