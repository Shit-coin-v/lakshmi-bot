import asyncio
import json
import hmac
import hashlib
from datetime import datetime, timezone

import aiohttp
import importlib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import config
from database.models import CustomUser
from onec_client import send_customer_to_onec


class DummySession:
    def __init__(self):
        self.committed = False
    async def commit(self):
        self.committed = True
    def add(self, obj):
        pass


def test_send_customer_to_onec(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test")
    monkeypatch.setenv("ONEC_CUSTOMER_URL", "http://example.com/onec/customer")
    monkeypatch.setenv("ONEC_API_KEY", "api_key")
    monkeypatch.setenv("ONEC_API_SECRET", "secret")
    importlib.reload(config)

    called = {}

    def fake_post(self, url, data=None, headers=None):
        called["url"] = url
        called["data"] = data
        called["headers"] = headers
        class FakeResponse:
            status = 200
            async def json(self):
                return {"one_c_guid": "GUID123", "bonus_balance": 5}
            async def text(self):
                return "ok"
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc, tb):
                pass
        return FakeResponse()

    monkeypatch.setattr(aiohttp.ClientSession, "post", fake_post, raising=False)

    user = CustomUser(
        telegram_id=1,
        qr_code="code",
        registration_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        bonuses=0
    )
    session = DummySession()

    asyncio.run(send_customer_to_onec(session, user, referrer_id=2))

    assert user.one_c_guid == "GUID123"
    assert session.committed
    payload = json.loads(called["data"])
    assert payload["telegram_id"] == 1
    assert payload["referrer_telegram_id"] == 2
    headers = called["headers"]
    assert headers["X-Api-Key"] == "api_key"
    assert "Idempotency-Key" in headers
    expected_sign = hmac.new(b"secret", called["data"].encode(), hashlib.sha256).hexdigest()
    assert headers["X-Sign"] == expected_sign
