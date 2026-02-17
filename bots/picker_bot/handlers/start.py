import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardRemove

from config import PICKER_ALLOWED_TG_IDS
from chat_cleanup import send_clean

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    telegram_id = message.from_user.id

    if telegram_id not in PICKER_ALLOWED_TG_IDS:
        logger.warning("Unauthorized access attempt: telegram_id=%s", telegram_id)
        await send_clean(message, "Доступ запрещён. Вы не зарегистрированы как сборщик.")
        return

    await send_clean(
        message,
        "Добро пожаловать в бот сборщика!\n"
        "Используйте кнопку меню ☰ для навигации.",
        reply_markup=ReplyKeyboardRemove(),
    )
