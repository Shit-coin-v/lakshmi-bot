import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.append(str(Path(__file__).resolve().parents[1]))

import chat_cleanup
from chat_cleanup import send_clean


def _make_message(chat_id=100, message_id=1, bot=None):
    msg = AsyncMock()
    msg.chat.id = chat_id
    msg.message_id = message_id
    msg.bot = bot or AsyncMock()

    sent = AsyncMock()
    sent.message_id = 999
    msg.answer = AsyncMock(return_value=sent)
    msg.delete = AsyncMock()
    return msg


def setup_function():
    """Reset tracked messages between tests."""
    chat_cleanup._last_bot_msg.clear()


def test_send_clean_deletes_user_message():
    msg = _make_message()
    asyncio.run(send_clean(msg, "hello"))
    msg.delete.assert_awaited_once()


def test_send_clean_sends_answer():
    msg = _make_message()
    asyncio.run(send_clean(msg, "hello"))
    msg.answer.assert_awaited_once_with("hello")


def test_send_clean_passes_kwargs():
    msg = _make_message()
    markup = MagicMock()
    asyncio.run(send_clean(msg, "text", reply_markup=markup))
    msg.answer.assert_awaited_once_with("text", reply_markup=markup)


def test_send_clean_tracks_message_id():
    msg = _make_message(chat_id=42)
    asyncio.run(send_clean(msg, "hello"))
    assert chat_cleanup._last_bot_msg[42] == 999


def test_send_clean_deletes_previous_bot_message():
    chat_cleanup._last_bot_msg[100] = 555
    msg = _make_message(chat_id=100)
    asyncio.run(send_clean(msg, "new"))
    msg.bot.delete_message.assert_awaited_once_with(100, 555)


def test_send_clean_no_previous_message():
    msg = _make_message(chat_id=200)
    asyncio.run(send_clean(msg, "first"))
    msg.bot.delete_message.assert_not_awaited()


def test_send_clean_handles_delete_error():
    msg = _make_message()
    msg.delete.side_effect = Exception("forbidden")
    result = asyncio.run(send_clean(msg, "hello"))
    assert result.message_id == 999


def test_send_clean_handles_old_message_delete_error():
    chat_cleanup._last_bot_msg[100] = 555
    msg = _make_message(chat_id=100)
    msg.bot.delete_message.side_effect = Exception("message not found")
    result = asyncio.run(send_clean(msg, "hello"))
    assert result.message_id == 999


def test_send_clean_returns_sent_message():
    msg = _make_message()
    result = asyncio.run(send_clean(msg, "hello"))
    assert result.message_id == 999
