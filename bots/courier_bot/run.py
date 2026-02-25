import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import COURIER_BOT_TOKEN
from handlers import start, registration, orders, help, toggle

logger = logging.getLogger(__name__)

dp = Dispatcher()
dp.message.filter(F.chat.type == "private")
dp.callback_query.filter(F.message.chat.type == "private")
dp.include_router(start.router)
dp.include_router(registration.router)
dp.include_router(orders.router)
dp.include_router(toggle.router)
dp.include_router(help.router)


async def main():
    bot = Bot(
        token=COURIER_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if not COURIER_BOT_TOKEN:
        logger.error("COURIER_BOT_TOKEN is not configured; courier bot will not start")
        raise SystemExit(1)
    asyncio.run(main())
