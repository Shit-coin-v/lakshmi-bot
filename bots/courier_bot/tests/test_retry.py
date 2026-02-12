import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

import retry
from retry import is_in_flight, retry_status_update, schedule_retry


def setup_function():
    retry._in_flight.clear()


# --- is_in_flight ---

def test_is_in_flight_no_task():
    assert is_in_flight(1) is False


def test_is_in_flight_done_task():
    task = MagicMock()
    task.done.return_value = True
    retry._in_flight[1] = task
    assert is_in_flight(1) is False


def test_is_in_flight_running_task():
    task = MagicMock()
    task.done.return_value = False
    retry._in_flight[1] = task
    assert is_in_flight(1) is True


# --- retry_status_update ---

def test_retry_success_first_attempt():
    """update_fn succeeds on first try -> on_success called."""
    bot = MagicMock()
    update_fn = AsyncMock(return_value=True)
    on_success = AsyncMock()
    on_failure = AsyncMock()

    asyncio.run(retry_status_update(
        bot=bot, chat_id=1, message_id=1, order_id=10,
        new_status="delivery", update_fn=update_fn,
        on_success=on_success, on_failure=on_failure,
    ))

    update_fn.assert_awaited_once_with(10, "delivery")
    on_success.assert_awaited_once_with(bot, 1, 1, 10, "delivery")
    on_failure.assert_not_awaited()


def test_retry_all_fail():
    """update_fn always fails -> on_failure called after all retries."""
    bot = MagicMock()
    update_fn = AsyncMock(return_value=False)
    on_success = AsyncMock()
    on_failure = AsyncMock()

    with patch("retry.asyncio.sleep", new_callable=AsyncMock):
        asyncio.run(retry_status_update(
            bot=bot, chat_id=1, message_id=1, order_id=10,
            new_status="delivery", update_fn=update_fn,
            on_success=on_success, on_failure=on_failure,
        ))

    assert update_fn.await_count == 6  # _RETRY_DELAYS has 6 entries
    on_success.assert_not_awaited()
    on_failure.assert_awaited_once()


def test_retry_success_on_third_attempt():
    """update_fn fails twice then succeeds -> on_success called."""
    bot = MagicMock()
    update_fn = AsyncMock(side_effect=[False, False, True])
    on_success = AsyncMock()
    on_failure = AsyncMock()

    with patch("retry.asyncio.sleep", new_callable=AsyncMock):
        asyncio.run(retry_status_update(
            bot=bot, chat_id=1, message_id=1, order_id=10,
            new_status="delivery", update_fn=update_fn,
            on_success=on_success, on_failure=on_failure,
        ))

    assert update_fn.await_count == 3
    on_success.assert_awaited_once()
    on_failure.assert_not_awaited()


def test_retry_clears_in_flight():
    """After retry completes, order is removed from _in_flight."""
    bot = MagicMock()
    update_fn = AsyncMock(return_value=True)
    on_success = AsyncMock()
    on_failure = AsyncMock()

    retry._in_flight[10] = MagicMock()

    asyncio.run(retry_status_update(
        bot=bot, chat_id=1, message_id=1, order_id=10,
        new_status="delivery", update_fn=update_fn,
        on_success=on_success, on_failure=on_failure,
    ))

    assert 10 not in retry._in_flight


def test_retry_update_fn_exception():
    """update_fn raises exception -> on_failure called."""
    bot = MagicMock()
    update_fn = AsyncMock(side_effect=RuntimeError("connection lost"))
    on_success = AsyncMock()
    on_failure = AsyncMock()

    asyncio.run(retry_status_update(
        bot=bot, chat_id=1, message_id=1, order_id=10,
        new_status="delivery", update_fn=update_fn,
        on_success=on_success, on_failure=on_failure,
    ))

    on_failure.assert_awaited_once()
    on_success.assert_not_awaited()


# --- schedule_retry ---

def test_schedule_retry_creates_task():
    """schedule_retry creates an asyncio task and tracks it."""
    bot = MagicMock()
    update_fn = AsyncMock(return_value=True)
    on_success = AsyncMock()
    on_failure = AsyncMock()

    async def run():
        task = schedule_retry(
            bot=bot, chat_id=1, message_id=1, order_id=20,
            new_status="completed", update_fn=update_fn,
            on_success=on_success, on_failure=on_failure,
        )
        assert is_in_flight(20)
        await task
        # After completion, in_flight is cleared
        assert not is_in_flight(20)

    asyncio.run(run())
