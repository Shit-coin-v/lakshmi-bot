import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("BOT_TOKEN", "123456:TESTTOKEN")

test_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(test_dir))
sys.path.append(str(test_dir.parent))

from shared.broadcast import helpers as _broadcast_helpers  # noqa: E402  pylint: disable=wrong-import-position
from shared.broadcast import generate_unique_open_token  # noqa: E402  pylint: disable=wrong-import-position
from run import register_newsletter_open  # noqa: E402  pylint: disable=wrong-import-position
import run  # noqa: E402  pylint: disable=wrong-import-position


def test_generate_unique_open_token(monkeypatch):
    async def run_test():
        tokens = ["a" * 32, "b" * 32]

        def fake_token_hex(length):
            return tokens.pop(0)

        async def fake_token_exists(token):
            return token == "a" * 32

        monkeypatch.setattr(_broadcast_helpers.secrets, "token_hex", fake_token_hex)

        token = await generate_unique_open_token(fake_token_exists)
        assert token == "b" * 32

    asyncio.run(run_test())


def test_register_newsletter_open_idempotent(monkeypatch):
    """First call returns newly_opened=True, second returns False."""
    call_count = 0

    async def mock_newsletter_open(token, telegram_user_id, raw_data=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "delivery_id": 2,
                "newly_opened": True,
                "message_text": "hidden text",
            }
        return {
            "delivery_id": 2,
            "newly_opened": False,
            "message_text": "hidden text",
        }

    monkeypatch.setattr(run.backend, "newsletter_open", mock_newsletter_open)

    async def first_call():
        result, opened = await register_newsletter_open(
            "c" * 32,
            telegram_user_id=202,
            raw_data="open:" + "c" * 32,
        )
        assert opened is True
        assert result["delivery_id"] == 2
        assert result["message_text"] == "hidden text"

    asyncio.run(first_call())

    async def second_call():
        result, opened = await register_newsletter_open(
            "c" * 32,
            telegram_user_id=202,
            raw_data="open:" + "c" * 32,
        )
        assert opened is False
        assert result["delivery_id"] == 2

    asyncio.run(second_call())


def test_register_newsletter_open_not_found(monkeypatch):
    """Token not found returns (None, False)."""
    async def mock_newsletter_open(token, telegram_user_id, raw_data=""):
        return None

    monkeypatch.setattr(run.backend, "newsletter_open", mock_newsletter_open)

    async def run_test():
        result, opened = await register_newsletter_open(
            "e" * 32,
            telegram_user_id=303,
            raw_data="open:" + "e" * 32,
        )
        assert result is None
        assert opened is False

    asyncio.run(run_test())
