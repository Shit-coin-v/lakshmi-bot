import logging

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


class RegistrationStates(StatesGroup):
    waiting_full_name = State()
    waiting_phone = State()


@router.message(RegistrationStates.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext):
    full_name = message.text.strip()
    if len(full_name) < 2:
        await send_clean(message, "Имя слишком короткое. Введите ФИО:")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationStates.waiting_phone)
    await send_clean(message, "Введите ваш номер телефона:")


@router.message(RegistrationStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if len(phone) < 6:
        await send_clean(message, "Некорректный номер. Введите номер телефона:")
        return

    data = await state.get_data()
    full_name = data["full_name"]

    result = await backend.register_staff(
        telegram_id=message.from_user.id,
        full_name=full_name,
        phone=phone,
        role="picker",
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
