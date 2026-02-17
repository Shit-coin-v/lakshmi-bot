import logging

from aiogram.types import Message

logger = logging.getLogger(__name__)

# chat_id -> last bot message_id
_last_bot_msg: dict[int, int] = {}


async def send_clean(message: Message, text: str, **kwargs) -> Message:
    """Send new message first, then delete old ones (avoids empty chat flash)."""
    chat_id = message.chat.id

    # 1) Send new message FIRST (chat is never empty)
    sent = await message.answer(text, **kwargs)

    # 2) Delete user's message
    try:
        await message.delete()
    except Exception:
        logger.debug("Could not delete user message %d", message.message_id)

    # 3) Delete previous bot message
    old_id = _last_bot_msg.get(chat_id)
    if old_id:
        try:
            await message.bot.delete_message(chat_id, old_id)
        except Exception:
            logger.debug("Could not delete old bot message %d", old_id)

    # 4) Track it
    _last_bot_msg[chat_id] = sent.message_id

    return sent


def track_message(chat_id: int, message_id: int):
    """Track a bot message sent outside send_clean (e.g. from callbacks)."""
    _last_bot_msg[chat_id] = message_id
