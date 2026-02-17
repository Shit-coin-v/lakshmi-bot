import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import PICKER_ALLOWED_TG_IDS
from chat_cleanup import send_clean

logger = logging.getLogger(__name__)

router = Router()

HELP_TEXT = (
    "Доступные команды:\n\n"
    "/orders — 📦 Новые заказы\n"
    "/active — 🔧 Мои заказы в работе\n"
    "/completed — 📋 Отчёт за сегодня\n"
    "/help — ❓ Помощь\n\n"
    "🔔 Уведомления о новых заказах приходят автоматически.\n\n"
    "Работа с заказами:\n"
    "1. Нажмите на заказ для просмотра деталей\n"
    "2. 📋 Принять — берёте заказ в работу\n"
    "3. 📦 Собираем — начинаете сборку\n"
    "4. ✅ Заказ собрал — сборка завершена\n"
    "5. 🤝 Клиент забрал — выдача самовывоза\n\n"
    "↩️ Вернуть заказ — вернуть в общий пул"
)


@router.message(Command("help"))
async def cmd_help(message: Message):
    if message.from_user.id not in PICKER_ALLOWED_TG_IDS:
        await send_clean(message, "Доступ запрещён.")
        return

    await send_clean(message, HELP_TEXT)
