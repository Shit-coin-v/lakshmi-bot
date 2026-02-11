import logging

from aiogram.types import InlineKeyboardMarkup, Message

from keyboards import get_main_menu

logger = logging.getLogger(__name__)

# chat_id -> last bot message_id
_last_bot_msg: dict[int, int] = {}


async def send_clean(message: Message, text: str, **kwargs) -> Message:
    """Delete user msg + old bot msg, send new one, track it."""
    chat_id = message.chat.id

    # 1) Delete user's message (button text)
    try:
        await message.delete()
    except Exception:
        logger.debug("Could not delete user message %d", message.message_id)

    # 2) Delete previous bot message
    old_id = _last_bot_msg.get(chat_id)
    if old_id:
        try:
            await message.bot.delete_message(chat_id, old_id)
        except Exception:
            logger.debug("Could not delete old bot message %d", old_id)

    # 3) Extract InlineKeyboard if present
    inline_kb = None
    if isinstance(kwargs.get("reply_markup"), InlineKeyboardMarkup):
        inline_kb = kwargs.pop("reply_markup")

    # 4) Default to ReplyKeyboard if no reply_markup specified
    if "reply_markup" not in kwargs:
        kwargs["reply_markup"] = get_main_menu()

    # 5) Send message with ReplyKeyboard (refreshes chat keyboard)
    sent = await message.answer(text, **kwargs)

    # 6) If InlineKeyboard was requested: send second message with it, delete the first
    if inline_kb:
        sent_inline = await message.answer(text, reply_markup=inline_kb)
        try:
            await message.bot.delete_message(chat_id, sent.message_id)
        except Exception:
            logger.debug("Could not delete ReplyKeyboard refresh message")
        sent = sent_inline

    # 7) Track it
    _last_bot_msg[chat_id] = sent.message_id

    return sent
