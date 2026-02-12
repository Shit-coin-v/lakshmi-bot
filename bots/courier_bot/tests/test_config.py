import importlib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import config


def test_courier_ids_parsed(monkeypatch):
    monkeypatch.setenv("COURIER_ALLOWED_TG_IDS", "111,222,333")
    monkeypatch.setenv("COURIER_BOT_TOKEN", "test")
    importlib.reload(config)
    assert config.COURIER_ALLOWED_TG_IDS == {111, 222, 333}


def test_courier_ids_empty(monkeypatch):
    monkeypatch.setenv("COURIER_ALLOWED_TG_IDS", "")
    monkeypatch.setenv("COURIER_BOT_TOKEN", "test")
    importlib.reload(config)
    assert config.COURIER_ALLOWED_TG_IDS == set()


def test_courier_ids_with_spaces(monkeypatch):
    monkeypatch.setenv("COURIER_ALLOWED_TG_IDS", " 111 , 222 ")
    monkeypatch.setenv("COURIER_BOT_TOKEN", "test")
    importlib.reload(config)
    assert config.COURIER_ALLOWED_TG_IDS == {111, 222}


def test_courier_ids_ignores_non_digits(monkeypatch):
    monkeypatch.setenv("COURIER_ALLOWED_TG_IDS", "111,abc,222")
    monkeypatch.setenv("COURIER_BOT_TOKEN", "test")
    importlib.reload(config)
    assert config.COURIER_ALLOWED_TG_IDS == {111, 222}


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
