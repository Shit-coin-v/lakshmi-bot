import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from config import COURIER_ALLOWED_TG_IDS
from chat_cleanup import send_clean

logger = logging.getLogger(__name__)

router = Router()

HELP_TEXT = (
    "Доступные команды:\n\n"
    "/start \u2014 Начало работы\n"
    "/help \u2014 Справка\n\n"
    "\U0001f514 Уведомления о новых заказах приходят автоматически.\n"
    "\U0001f4e6 Заказы \u2014 список активных заказов\n\n"
    "Работа с заказами:\n"
    "1. Нажмите на заказ для просмотра деталей\n"
    "2. \U0001f697 Забрал заказ \u2014 заказ собран, вы забрали его\n"
    "3. \U0001f4cd Я на месте \u2014 вы приехали к клиенту\n"
    "4. \u2705 Доставлено \u2014 заказ передан клиенту"
)


@router.message(Command("help"))
async def cmd_help(message: Message):
    if message.from_user.id not in COURIER_ALLOWED_TG_IDS:
        await send_clean(message, "Доступ запрещён.")
        return

    await send_clean(message, HELP_TEXT)


@router.message(F.text == "\u2753 \u041f\u043e\u043c\u043e\u0449\u044c")
async def btn_help(message: Message):
    if message.from_user.id not in COURIER_ALLOWED_TG_IDS:
        await send_clean(message, "Доступ запрещён.")
        return

    await send_clean(message, HELP_TEXT)
