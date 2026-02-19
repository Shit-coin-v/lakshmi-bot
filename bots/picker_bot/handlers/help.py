import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from shared.clients.backend_client import BackendClient
from config import BACKEND_URL, INTEGRATION_API_KEY
from shared.bot_utils.chat_cleanup import send_clean

logger = logging.getLogger(__name__)

router = Router()

backend = BackendClient(BACKEND_URL, INTEGRATION_API_KEY)

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
    result = await backend.check_staff_access(message.from_user.id, "picker")
    if result is None or result.get("status") != "approved":
        await send_clean(message, "Доступ запрещён.")
        return

    await send_clean(message, HELP_TEXT)
