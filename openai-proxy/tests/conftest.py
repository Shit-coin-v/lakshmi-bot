"""Pytest-фикстуры для openai-proxy."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Добавляем корень openai-proxy/ в sys.path, чтобы 'from app.main ...' работал
# из любого CWD (pytest, IDE, CI).
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Изолируем тесты от .env-файла на диске и реальных секретов."""

    for key in (
        "OPENAI_API_KEY",
        "INTERNAL_API_KEY",
        "OPENAI_REQUEST_TIMEOUT",
        "MAX_IMAGE_SIZE_BYTES",
        "LOG_LEVEL",
    ):
        monkeypatch.delenv(key, raising=False)
    yield


@pytest.fixture
def configured_env(monkeypatch):
    """Фикстура с заполненными ключами для happy-path сценариев."""

    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("INTERNAL_API_KEY", "test-internal-key")
    monkeypatch.setenv("MAX_IMAGE_SIZE_BYTES", "1048576")
    # Сбрасываем кэш singleton'а настроек.
    from app import config

    config._settings = None
    yield
    config._settings = None


@pytest.fixture
def client(configured_env):
    """TestClient FastAPI с настроенными env."""

    # Импорт после фикстуры env, чтобы Settings подхватили монкипатч.
    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
