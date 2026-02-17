import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from shared.clients.backend_client import BackendClient
from config import COURIER_ALLOWED_TG_IDS, BACKEND_URL, INTEGRATION_API_KEY
from shared.bot_utils.chat_cleanup import send_clean

logger = logging.getLogger(__name__)

router = Router()

backend = BackendClient(BACKEND_URL, INTEGRATION_API_KEY)


@router.message(Command("toggle"))
async def cmd_toggle(message: Message):
    if message.from_user.id not in COURIER_ALLOWED_TG_IDS:
        await send_clean(message, "Доступ запрещён.")
        return

    tg_id = message.from_user.id

    # Get current state
    profile = await backend.get_courier_profile(tg_id)
    if profile is None:
        await send_clean(message, "❌ Не удалось получить профиль.")
        return

    current = profile.get("accepting_orders", True)
    new_value = not current

    result = await backend.toggle_accepting(tg_id, new_value)
    if result is None:
        await send_clean(message, "❌ Не удалось обновить статус.")
        return

    if result.get("accepting_orders"):
        await send_clean(message, "✅ Вы принимаете заказы.\nНовые заказы будут назначаться вам автоматически.")
    else:
        await send_clean(message, "⛔ Приём заказов остановлен.\nНовые заказы не будут назначаться.")
