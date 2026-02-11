import logging

from aiogram.types import InlineKeyboardMarkup, Message

from keyboards import get_main_menu

logger = logging.getLogger(__name__)

# chat_id -> list of tracked bot message_ids
_last_bot_msgs: dict[int, list[int]] = {}


async def send_clean(message: Message, text: str, **kwargs) -> Message:
    """Delete user msg + old bot msgs, send new one(s), track them."""
    chat_id = message.chat.id

    # 1) Delete user's message (button text)
    try:
        await message.delete()
    except Exception:
        logger.debug("Could not delete user message %d", message.message_id)

    # 2) Delete previous bot messages
    for old_id in _last_bot_msgs.get(chat_id, []):
        try:
            await message.bot.delete_message(chat_id, old_id)
        except Exception:
            logger.debug("Could not delete old bot message %d", old_id)

    # 3) Send message(s)
    reply_markup = kwargs.get("reply_markup")
    msg_ids = []

    if isinstance(reply_markup, InlineKeyboardMarkup):
        # Send ReplyKeyboard first to keep menu visible
        menu_msg = await message.answer("·", reply_markup=get_main_menu())
        msg_ids.append(menu_msg.message_id)
        # Then send the actual content with InlineKeyboard
        sent = await message.answer(text, **kwargs)
        msg_ids.append(sent.message_id)
    else:
        if "reply_markup" not in kwargs:
            kwargs["reply_markup"] = get_main_menu()
        sent = await message.answer(text, **kwargs)
        msg_ids.append(sent.message_id)

    # 4) Track for cleanup
    _last_bot_msgs[chat_id] = msg_ids

    return sent
