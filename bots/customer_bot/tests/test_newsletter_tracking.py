import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError

os.environ.setdefault("BOT_TOKEN", "123456:TESTTOKEN")

test_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(test_dir))
sys.path.append(str(test_dir.parent))

from broadcast import generate_unique_open_token  # noqa: E402  pylint: disable=wrong-import-position
from shared.broadcast import helpers as _broadcast_helpers  # noqa: E402  pylint: disable=wrong-import-position
from database import models as db_models  # noqa: E402  pylint: disable=wrong-import-position
from run import register_newsletter_open  # noqa: E402  pylint: disable=wrong-import-position


class DummyResult:
    def __init__(self, delivery):
        self._delivery = delivery

    def scalar_one_or_none(self):
        return self._delivery


class DummyTransaction:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is None:
            self._session.commits += 1
        if self._session._override_opened_at is not None:
            self._session.state.delivery.opened_at = self._session.state.actual_opened_at
        return False


class SharedState:
    def __init__(self, delivery):
        self.delivery = delivery
        self.added = []
        self.events = []
        self.event_created = False
        self.actual_opened_at = delivery.opened_at
        self.raise_on_duplicate = False
        self.rollbacks = 0


class DummySession:
    def __init__(self, state: SharedState, *, override_opened_at=None, force_duplicate=False):
        self.state = state
        self._override_opened_at = override_opened_at
        self._force_duplicate = force_duplicate
        self.commits = 0

    def begin(self):
        return DummyTransaction(self)

    async def execute(self, statement):  # pragma: no cover - statement content not relevant
        if self._override_opened_at is not None:
            self.state.delivery.opened_at = self._override_opened_at
        return DummyResult(self.state.delivery)

    def add(self, obj):
        self.state.added.append(obj)
        if isinstance(obj, db_models.NewsletterOpenEvent):
            if self._force_duplicate or (
                self.state.event_created and self.state.raise_on_duplicate
            ):
                raise IntegrityError("duplicate", params=None, orig=None)
            self.state.event_created = True
            self.state.events.append(obj)
            self.state.actual_opened_at = self.state.delivery.opened_at

    async def rollback(self):
        self.state.rollbacks += 1
        self.state.delivery.opened_at = self.state.actual_opened_at


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


def test_sqlalchemy_delivery_uses_message_id():
    message = db_models.BroadcastMessage(id=10, message_text="hello")
    delivery = db_models.NewsletterDelivery(
        id=1,
        message_id=message.id,
        customer_id=1,
        chat_id=1001,
        telegram_message_id=55,
        open_token="d" * 32,
    )
    delivery.message = message

    assert delivery.message_id == message.id
    assert delivery.message is message


def test_register_newsletter_open_idempotent():
    message = db_models.BroadcastMessage(id=20, message_text="hidden text")
    delivery = db_models.NewsletterDelivery(
        id=2,
        message_id=message.id,
        customer_id=2,
        chat_id=777,
        telegram_message_id=88,
        open_token="c" * 32,
    )
    delivery.message = message
    state = SharedState(delivery)

    async def first_call():
        session = DummySession(state)
        stored_delivery, opened = await register_newsletter_open(
            session,
            delivery.open_token,
            telegram_user_id=202,
            raw_data=f"open:{delivery.open_token}",
        )
        assert opened is True
        assert stored_delivery.opened_at is delivery.opened_at
        assert isinstance(stored_delivery.opened_at, datetime)

    asyncio.run(first_call())

    first_opened_at = delivery.opened_at
    assert state.event_created is True
    assert len(state.events) == 1

    async def second_call():
        session = DummySession(state)
        stored_delivery, opened = await register_newsletter_open(
            session,
            delivery.open_token,
            telegram_user_id=202,
            raw_data=f"open:{delivery.open_token}",
        )
        assert opened is False
        assert stored_delivery.opened_at == first_opened_at

    asyncio.run(second_call())

    assert state.rollbacks == 0
    assert len(state.events) == 1


def test_register_newsletter_open_race_condition():
    message = db_models.BroadcastMessage(id=30, message_text="promo")
    delivery = db_models.NewsletterDelivery(
        id=3,
        message_id=message.id,
        customer_id=3,
        chat_id=900,
        telegram_message_id=91,
        open_token="e" * 32,
    )
    delivery.message = message
    state = SharedState(delivery)
    state.raise_on_duplicate = True

    async def run_race():
        async def open_primary():
            session = DummySession(state)
            return await register_newsletter_open(
                session,
                delivery.open_token,
                telegram_user_id=303,
                raw_data=f"open:{delivery.open_token}",
            )

        async def open_secondary():
            await asyncio.sleep(0)
            session = DummySession(state, override_opened_at=None, force_duplicate=True)
            return await register_newsletter_open(
                session,
                delivery.open_token,
                telegram_user_id=303,
                raw_data=f"open:{delivery.open_token}",
            )

        return await asyncio.gather(open_primary(), open_secondary())

    first_result, second_result = asyncio.run(run_race())

    assert {first_result[1], second_result[1]} == {True, False}
    assert len(state.events) == 1
    assert delivery.opened_at == state.actual_opened_at
