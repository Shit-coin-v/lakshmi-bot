import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import COURIER_ALLOWED_TG_IDS
from chat_cleanup import send_clean

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
    if message.from_user.id not in COURIER_ALLOWED_TG_IDS:
        await send_clean(message, "Доступ запрещён.")
        return

    await send_clean(message, HELP_TEXT)
