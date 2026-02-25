import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from shared.bot_utils.chat_cleanup import send_clean
from config import backend

logger = logging.getLogger(__name__)

router = Router()

HELP_TEXT = (
    "Доступные команды:\n\n"
    "/orders — 📦 Мои заказы\n"
    "/toggle — 🔄 Принимать/Остановить заказы\n"
    "/completed — 📋 Отчёт за сегодня\n"
    "/help — ❓ Помощь\n\n"
    "🔔 Заказы назначаются автоматически.\n\n"
    "Работа с заказами:\n"
    "1. Заказ назначается вам автоматически\n"
    "2. 🚗 Забрал заказ — начинаете доставку\n"
    "3. 📍 Я на месте — прибыли к клиенту\n"
    "4. ✅ Доставлено — доставка завершена\n\n"
    "🔄 /toggle — остановить/возобновить приём заказов"
)


@router.message(Command("help"))
async def cmd_help(message: Message):
    result = await backend.check_staff_access(message.from_user.id, "courier")
    if result is None or result.get("status") != "approved":
        await send_clean(message, "Доступ запрещён.")
        return

    await send_clean(message, HELP_TEXT)
