import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    MenuButtonCommands,
    MenuButtonDefault,
    Message,
    ReplyKeyboardRemove,
)

from shared.clients.backend_client import BackendClient
from config import BACKEND_URL, INTEGRATION_API_KEY
from shared.bot_utils.chat_cleanup import send_clean
from .registration import RegistrationStates

logger = logging.getLogger(__name__)

router = Router()

backend = BackendClient(BACKEND_URL, INTEGRATION_API_KEY)

COMMANDS = [
    BotCommand(command="orders", description="Новые заказы"),
    BotCommand(command="active", description="Мои заказы"),
    BotCommand(command="completed", description="Отчёт"),
    BotCommand(command="help", description="Помощь"),
]


async def _set_menu(bot, chat_id: int, approved: bool):
    """Show or hide menu commands for a specific chat."""
    if approved:
        await bot.set_my_commands(COMMANDS, scope=BotCommandScopeChat(chat_id=chat_id))
        await bot.set_chat_menu_button(chat_id=chat_id, menu_button=MenuButtonCommands())
    else:
        await bot.set_my_commands([], scope=BotCommandScopeChat(chat_id=chat_id))
        await bot.set_chat_menu_button(chat_id=chat_id, menu_button=MenuButtonDefault())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    chat_id = message.chat.id

    # Check access via DB
    result = await backend.check_staff_access(telegram_id, "picker")

    if result is None:
        # Not found — hide menu, start registration FSM
        await _set_menu(message.bot, chat_id, approved=False)
        await state.set_state(RegistrationStates.waiting_full_name)
        await send_clean(
            message,
            "Добро пожаловать! Для регистрации введите ваше ФИО:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    status = result.get("status")

    if status == "blacklisted":
        await _set_menu(message.bot, chat_id, approved=False)
        await send_clean(message, "Доступ запрещён.")
        return

    if status == "pending":
        await _set_menu(message.bot, chat_id, approved=False)
        await send_clean(
            message,
            "Ваша заявка на рассмотрении. Ожидайте подтверждения администратора.",
        )
        return

    if status == "approved":
        # Show menu commands
        await _set_menu(message.bot, chat_id, approved=True)

        await send_clean(
            message,
            "Добро пожаловать в бот сборщика!\n"
            "Используйте кнопку меню ☰ для навигации.",
            reply_markup=ReplyKeyboardRemove(),
        )
