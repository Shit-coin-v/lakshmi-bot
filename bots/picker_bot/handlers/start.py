import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from shared.clients.backend_client import BackendClient
from config import BACKEND_URL, INTEGRATION_API_KEY
from shared.bot_utils.chat_cleanup import send_clean
from .registration import RegistrationStates

logger = logging.getLogger(__name__)

router = Router()

backend = BackendClient(BACKEND_URL, INTEGRATION_API_KEY)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id

    # Check access via DB
    result = await backend.check_staff_access(telegram_id, "picker")

    if result is None:
        # Not found — start registration FSM
        await state.set_state(RegistrationStates.waiting_full_name)
        await send_clean(
            message,
            "Добро пожаловать! Для регистрации введите ваше ФИО:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    status = result.get("status")

    if status == "blacklisted":
        await send_clean(message, "Доступ запрещён.")
        return

    if status == "pending":
        await send_clean(
            message,
            "Ваша заявка на рассмотрении. Ожидайте подтверждения администратора.",
        )
        return

    if status == "approved":
        await send_clean(
            message,
            "Добро пожаловать в бот сборщика!\n"
            "Используйте кнопку меню ☰ для навигации.",
            reply_markup=ReplyKeyboardRemove(),
        )
