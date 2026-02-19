import importlib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import config


def test_backend_url_default(monkeypatch):
    monkeypatch.delenv("BACKEND_URL", raising=False)
    monkeypatch.setenv("COURIER_BOT_TOKEN", "test")
    importlib.reload(config)
    assert config.BACKEND_URL == "http://app:8000"


def test_backend_url_from_env(monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "http://localhost:9000")
    monkeypatch.setenv("COURIER_BOT_TOKEN", "test")
    importlib.reload(config)
    assert config.BACKEND_URL == "http://localhost:9000"
