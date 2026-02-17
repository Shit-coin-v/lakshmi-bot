import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardRemove

from shared.clients.backend_client import BackendClient
from config import COURIER_ALLOWED_TG_IDS, BACKEND_URL, INTEGRATION_API_KEY
from chat_cleanup import send_clean

logger = logging.getLogger(__name__)

router = Router()

backend = BackendClient(BACKEND_URL, INTEGRATION_API_KEY)


@router.message(CommandStart())
async def cmd_start(message: Message):
    telegram_id = message.from_user.id

    if telegram_id not in COURIER_ALLOWED_TG_IDS:
        logger.warning("Unauthorized access attempt: telegram_id=%s", telegram_id)
        await send_clean(message, "Доступ запрещён. Вы не зарегистрированы как курьер.")
        return

    # Ensure courier profile exists (for round-robin assignment)
    await backend.get_courier_profile(telegram_id)

    await send_clean(
        message,
        "Добро пожаловать в бот курьера!\n"
        "Заказы назначаются автоматически.\n"
        "Используйте кнопку меню ☰ для навигации.",
        reply_markup=ReplyKeyboardRemove(),
    )
