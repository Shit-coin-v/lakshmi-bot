import asyncio
import json
from unittest.mock import AsyncMock

import aiohttp
import importlib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import config
import onec_client
from onec_client import send_customer_to_onec


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

    user_data = {
        "id": 42,
        "telegram_id": 1,
        "qr_code": "code",
        "registration_date": "2025-01-01T00:00:00+00:00",
        "bonuses": "0.00",
    }

    # Mock backend_client methods
    mock_upsert = AsyncMock()
    mock_patch = AsyncMock()
    monkeypatch.setattr(onec_client.backend, "upsert_onec_map", mock_upsert)
    monkeypatch.setattr(onec_client.backend, "patch_user", mock_patch)

    asyncio.run(send_customer_to_onec(user_data, referrer_id=2))

    # Verify 1C API call
    payload = json.loads(called["data"])
    assert payload["telegram_id"] == 1
    assert payload["referrer_telegram_id"] == 2
    headers = called["headers"]
    assert headers["X-Api-Key"] == "api_key"
    assert "X-Idempotency-Key" in headers

    # Verify backend_client calls
    mock_upsert.assert_awaited_once_with(42, "GUID123")
    mock_patch.assert_awaited_once_with(42, {"bonuses": "5"})
