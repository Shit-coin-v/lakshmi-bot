import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import COURIER_ALLOWED_TG_IDS
from keyboards import get_main_menu

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    telegram_id = message.from_user.id

    if telegram_id not in COURIER_ALLOWED_TG_IDS:
        logger.warning("Unauthorized access attempt: telegram_id=%s", telegram_id)
        await message.answer("Доступ запрещён. Вы не зарегистрированы как курьер.")
        return

    await message.answer(
        "Добро пожаловать в бот курьера!\n"
        "Используйте меню для навигации.",
        reply_markup=get_main_menu(),
    )
