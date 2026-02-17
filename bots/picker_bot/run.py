import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, MenuButtonCommands

from config import PICKER_BOT_TOKEN
from handlers import start, orders, help

logger = logging.getLogger(__name__)

dp = Dispatcher()
dp.include_router(start.router)
dp.include_router(orders.router)
dp.include_router(help.router)


@dp.startup()
async def on_startup(bot: Bot):
    await bot.set_my_commands(
        commands=[
            BotCommand(command="orders", description="📦 Новые заказы"),
            BotCommand(command="active", description="🔧 Мои заказы"),
            BotCommand(command="completed", description="📋 Отчёт"),
            BotCommand(command="help", description="❓ Помощь"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
    )
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())


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
