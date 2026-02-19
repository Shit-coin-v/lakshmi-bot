import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import PICKER_BOT_TOKEN
from handlers import start, registration, orders, help

logger = logging.getLogger(__name__)

dp = Dispatcher()
dp.include_router(start.router)
dp.include_router(registration.router)
dp.include_router(orders.router)
dp.include_router(help.router)


async def main():
    bot = Bot(
        token=PICKER_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if not PICKER_BOT_TOKEN:
        logger.error("PICKER_BOT_TOKEN is not configured; picker bot will not start")
        raise SystemExit(1)
    asyncio.run(main())
