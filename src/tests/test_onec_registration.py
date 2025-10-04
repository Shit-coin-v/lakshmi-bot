import asyncio
import json
from datetime import datetime, timezone

import aiohttp
import importlib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import config
from database.models import CustomUser
import onec_client
from onec_client import send_customer_to_onec


class DummySession:
    def __init__(self):
        self.committed = False
        self.refreshed = False
        self.rolled_back = False
    async def commit(self):
        self.committed = True
    def add(self, obj):
        pass
    async def refresh(self, obj):
        self.refreshed = True
    async def rollback(self):
        self.rolled_back = True


def test_send_customer_to_onec(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test")
    monkeypatch.setenv("ONEC_CUSTOMER_URL", "http://example.com/onec/customer")
    monkeypatch.setenv("ONEC_API_KEY", "api_key")
    monkeypatch.setenv("INTEGRATION_API_KEY", "api_key")
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
                return json.dumps({"one_c_guid": "GUID123", "bonus_balance": 5})
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
    user.id = 42
    session = DummySession()

    async def fake_upsert(sess, user_id, guid):
        called["upsert"] = (user_id, guid)
        await sess.commit()

    monkeypatch.setattr(onec_client, "upsert_onec_client_map", fake_upsert)

    asyncio.run(send_customer_to_onec(session, user, referrer_id=2))

    assert called["upsert"] == (42, "GUID123")
    assert session.committed
    assert session.refreshed
    assert not session.rolled_back
    assert user.bonuses == 5
    payload = json.loads(called["data"])
    assert payload["telegram_id"] == 1
    assert payload["referrer_telegram_id"] == 2
    headers = called["headers"]
    assert headers["X-Api-Key"] == "api_key"
    assert "X-Idempotency-Key" in headers
    assert "X-Timestamp" not in headers
    assert "X-Sign" not in headers
