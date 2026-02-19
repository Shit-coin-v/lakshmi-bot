import logging
import re

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from shared.clients.backend_client import BackendClient
from config import BACKEND_URL, INTEGRATION_API_KEY
from shared.bot_utils.chat_cleanup import send_clean

logger = logging.getLogger(__name__)

router = Router()

backend = BackendClient(BACKEND_URL, INTEGRATION_API_KEY)

_NAME_RE = re.compile(r"^[а-яА-ЯёЁa-zA-Z\s\-\.]+$")
_PHONE_RE = re.compile(r"^\+?\d{10,15}$")


class RegistrationStates(StatesGroup):
    waiting_full_name = State()
    waiting_phone = State()


@router.message(RegistrationStates.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if text.startswith("/"):
        await send_clean(message, "Сейчас идёт регистрация. Введите ваше ФИО:")
        return

    if len(text) < 2 or not _NAME_RE.match(text):
        await send_clean(message, "ФИО должно содержать только буквы. Введите ФИО:")
        return

    await state.update_data(full_name=text)
    await state.set_state(RegistrationStates.waiting_phone)
    await send_clean(message, "Введите ваш номер телефона (например, +79001234567):")


@router.message(RegistrationStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if text.startswith("/"):
        await send_clean(message, "Сейчас идёт регистрация. Введите номер телефона:")
        return

    # Clean: remove spaces, dashes, parentheses
    phone = re.sub(r"[\s\-\(\)]", "", text)

    if not _PHONE_RE.match(phone):
        await send_clean(
            message,
            "Некорректный номер. Введите телефон цифрами (например, +79001234567):",
        )
        return

    data = await state.get_data()
    full_name = data["full_name"]

    result = await backend.register_staff(
        telegram_id=message.from_user.id,
        full_name=full_name,
        phone=phone,
        role="courier",
    )

    await state.clear()

    if result:
        await send_clean(
            message,
            f"Заявка отправлена!\n\n"
            f"ФИО: {full_name}\n"
            f"Телефон: {phone}\n\n"
            f"Ожидайте подтверждения администратора.",
        )
    else:
        await send_clean(message, "Ошибка при регистрации. Попробуйте /start заново.")
