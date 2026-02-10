import logging

from aiogram import F, Router
from aiogram.types import Message

from config import COURIER_ALLOWED_TG_IDS

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "\U0001f4e6 \u041c\u043e\u0438 \u0437\u0430\u043a\u0430\u0437\u044b")
async def my_orders(message: Message):
    if message.from_user.id not in COURIER_ALLOWED_TG_IDS:
        await message.answer("Доступ запрещён.")
        return

    await message.answer(
        "Функция просмотра заказов временно недоступна. Ожидайте обновлений."
    )
