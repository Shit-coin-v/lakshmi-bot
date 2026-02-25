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

from config import backend
from shared.bot_utils.chat_cleanup import send_clean
from shared.bot_utils.notifications import cleanup_notifications
from .registration import RegistrationStates

logger = logging.getLogger(__name__)

router = Router()

COMMANDS = [
    BotCommand(command="orders", description="Мои заказы"),
    BotCommand(command="toggle", description="Принимать/Остановить заказы"),
    BotCommand(command="completed", description="Отчёт заказов"),
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

    # Сброс FSM — предотвращает застревание в регистрации при повторном /start
    await state.clear()

    # Cleanup any pending notification messages (approval, new order, etc.)
    await cleanup_notifications(backend, message.bot, chat_id, telegram_id, "courier")

    # Check access via DB
    result = await backend.check_staff_access(telegram_id, "courier")

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

        # Ensure courier profile exists (for round-robin assignment)
        await backend.get_courier_profile(telegram_id)

        await send_clean(
            message,
            "Добро пожаловать в бот курьера!\n"
            "Заказы назначаются автоматически.\n"
            "Используйте кнопку меню ☰ для навигации.",
            reply_markup=ReplyKeyboardRemove(),
        )
