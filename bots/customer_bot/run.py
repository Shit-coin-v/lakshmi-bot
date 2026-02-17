import asyncio
import logging
import re

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand, BotCommandScopeAllPrivateChats, CallbackQuery,
    FSInputFile, MenuButtonCommands, Message,
)
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import StatesGroup
from aiogram.fsm.context import FSMContext

import config
from onec_client import send_customer_to_onec
from shared.bot_utils.chat_cleanup import send_clean, track_message
from keyboards import get_qr_code_button, get_back_to_menu_button, get_consent_button
from shared.clients.backend_client import BackendClient
from qr_code import (
    resolve_qr_code_path,
    generate_qr_code,
    qr_code_filename,
)

logger = logging.getLogger(__name__)

backend = BackendClient(config.BACKEND_URL, config.ONEC_API_KEY or "")

bot: Bot | None = None
dp = Dispatcher()

OPEN_CALLBACK_PREFIX = "open:"
TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")

HELP_TEXT = (
    "❓ Как пользоваться ботом:\n\n"
    "📲 Показать QR-код — покажите QR-код на кассе для начисления бонусов\n"
    "💰 Показать бонусы — текущий баланс бонусных баллов\n"
    "👥 Пригласить друга — реферальная ссылка для друзей\n\n"
    "Команды:\n"
    "/menu — 🏠 Главное меню\n"
    "/help — ❓ Помощь"
)


@dp.startup()
async def on_startup(bot: Bot):
    await bot.set_my_commands(
        commands=[
            BotCommand(command="menu", description="🏠 Главное меню"),
            BotCommand(command="help", description="❓ Помощь"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
    )
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())


async def register_newsletter_open(
    token: str,
    telegram_user_id: int,
    raw_data: str,
):
    """Register a newsletter open event via HTTP API."""
    result = await backend.newsletter_open(token, telegram_user_id, raw_data)
    if result is None:
        return None, False
    return result, result.get("newly_opened", False)


def get_bot() -> Bot:
    if bot is None:
        raise RuntimeError("Telegram bot is not initialised")
    return bot


class Registration(StatesGroup):
    pass


async def save_bot_activity(telegram_id: int, action: str):
    """Сохраняет активность пользователя через HTTP API."""
    await backend.create_activity(telegram_id, action)


async def ensure_qr_code_path(user_data: dict):
    """Возвращает путь к файлу QR-кода, восстанавливая его при необходимости."""
    if not user_data or not user_data.get("qr_code"):
        return None

    qr_code_value = str(user_data["qr_code"]).strip()
    telegram_id = user_data["telegram_id"]
    user_id = user_data["id"]
    path = None
    normalized_url = None

    try:
        path, normalized_url = resolve_qr_code_path(
            qr_code_value, telegram_id=telegram_id
        )
    except ValueError:
        logger.warning(
            "Не удалось преобразовать значение QR-кода в путь (telegram_id=%s, value=%r)",
            telegram_id,
            qr_code_value,
        )
    else:
        if path.exists():
            if normalized_url and normalized_url != qr_code_value:
                await backend.patch_user(user_id, {"qr_code": normalized_url})
            return path
        logger.warning(
            "Файл QR-кода не найден на диске (telegram_id=%s, path=%s)",
            telegram_id,
            path,
        )

    data_for_qr = qr_code_value if qr_code_value and path is None else str(telegram_id)
    filename = qr_code_filename(telegram_id)
    new_qr_value = generate_qr_code(
        data_for_qr, filename=filename, telegram_id=telegram_id
    )
    if qr_code_value != new_qr_value:
        await backend.patch_user(user_id, {"qr_code": new_qr_value})
    new_path, _ = resolve_qr_code_path(new_qr_value, telegram_id=telegram_id)
    return new_path


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext):
    user = await backend.get_user_by_telegram_id(message.from_user.id)

    if user:
        await ensure_qr_code_path(user)
        await send_clean(message, "🏠 Вы в главном меню", reply_markup=get_qr_code_button())
        return
    else:
        command_args = message.text.split()
        referrer_id = None
        if len(command_args) > 1 and command_args[1].startswith('ref'):
            try:
                referrer_id = int(command_args[1][3:])
                if not await backend.get_user_by_telegram_id(referrer_id):
                    referrer_id = None
            except ValueError:
                referrer_id = None

        await state.update_data(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            referrer_id=referrer_id
        )

        await send_clean(
            message,
            "👋 Здравствуйте!\n"
            "Добро пожаловать в нашу систему лояльности.\n"
            "Прежде чем начать, пожалуйста, ознакомьтесь с условиями обработки персональных данных.\n\n"
            "📄 Полный текст политики доступен здесь:\n"
            "👉 https://docs.google.com/document/d/13BI-g30MvueQS2fSvaVdnKA9M2LkyEBUTaJ0GFI5f2g/edit?usp=sharing\n\n"
            "Нажимая кнопку «Я согласен», вы подтверждаете своё согласие на обработку персональных данных "
            "в соответствии с Федеральным законом №152-ФЗ.\n\n"
            "⬇️ Пожалуйста, нажмите кнопку «Я согласен», чтобы продолжить.",
            reply_markup=get_consent_button(),
        )


@dp.callback_query(lambda c: c.data == "personal_data_agree")
async def consent_callback(callback: CallbackQuery, state: FSMContext):
    existing_user = await backend.get_user_by_telegram_id(callback.from_user.id)
    if existing_user:
        await callback.message.answer("Вы уже зарегистрированы.")
        return await callback.answer()

    await state.update_data(personal_data_consent=True)
    data = await state.get_data()

    # Generate QR code locally before registration
    qr_code = generate_qr_code(
        callback.from_user.id, telegram_id=callback.from_user.id
    )

    user = await backend.register_user({
        "telegram_id": callback.from_user.id,
        "first_name": callback.from_user.first_name,
        "last_name": callback.from_user.last_name,
        "referrer_id": data.get("referrer_id"),
        "personal_data_consent": True,
        "qr_code": qr_code,
    })

    # Delete the consent message
    try:
        await callback.message.delete()
    except Exception:
        pass

    if user:
        await send_customer_to_onec(user, data.get("referrer_id"))
        sent = await callback.message.answer(
            "Спасибо! Вы успешно зарегистрированы.\n\n🏠 Вы в главном меню",
            reply_markup=get_qr_code_button(),
        )
        track_message(callback.message.chat.id, sent.message_id)
    else:
        sent = await callback.message.answer(
            "Произошла ошибка при регистрации. Попробуйте позже или напишите /start."
        )
        track_message(callback.message.chat.id, sent.message_id)
    await state.clear()
    await callback.answer()


@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    user = await backend.get_user_by_telegram_id(message.from_user.id)
    if user:
        await ensure_qr_code_path(user)
        await send_clean(message, "🏠 Вы в главном меню", reply_markup=get_qr_code_button())
    else:
        await send_clean(message, "Вы ещё не зарегистрированы. Нажмите /start")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await send_clean(message, HELP_TEXT)


@dp.callback_query(lambda c: c.data in ["show_qr", "show_bonuses", "invite_friend"])
async def callback_handler(callback: CallbackQuery):
    user = await backend.get_user_by_telegram_id(callback.from_user.id)

    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    await save_bot_activity(telegram_id=callback.from_user.id, action=callback.data)

    if callback.data == "show_qr":
        qr_path = await ensure_qr_code_path(user)
        if not qr_path or not qr_path.exists():
            await callback.answer("QR-код не найден. Обратитесь в поддержку", show_alert=True)
            return

        photo = FSInputFile(str(qr_path))
        await callback.message.delete()
        await callback.message.answer_photo(photo, reply_markup=get_back_to_menu_button())

    elif callback.data == "show_bonuses":
        await callback.message.edit_text(
            f"💰 Ваши бонусы: {user['bonuses']}",
            reply_markup=get_back_to_menu_button(),
        )

    elif callback.data == "invite_friend":
        bot_info = await get_bot().get_me()
        bot_username = bot_info.username
        ref_link = f"https://t.me/{bot_username}?start=ref{user['telegram_id']}"
        await callback.message.edit_text(
            f"🔗 Ваша реферальная ссылка:\n{ref_link}",
            reply_markup=get_back_to_menu_button(),
        )

    await callback.answer()


@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    user = await backend.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    try:
        await callback.message.edit_text(
            "🏠 Вы в главном меню",
            reply_markup=get_qr_code_button(),
        )
    except TelegramBadRequest:
        # Message is a photo (from show_qr) — can't edit_text, delete and send new
        await callback.message.delete()
        sent = await callback.message.answer(
            "🏠 Вы в главном меню",
            reply_markup=get_qr_code_button(),
        )
        track_message(callback.message.chat.id, sent.message_id)
    await callback.answer()


@dp.message(Command("link"))
async def cmd_link(message: Message):
    """Handle /link <code> — link Telegram to an email account."""
    args = (message.text or "").split()
    if len(args) < 2 or not args[1].strip().isdigit():
        await send_clean(
            message,
            "Использование: /link <6-значный код>\n"
            "Получите код в приложении: Профиль → Привязать Telegram",
        )
        return

    code = args[1].strip()
    telegram_id = message.from_user.id

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{config.BACKEND_URL}/api/auth/link-telegram/confirm/"
            headers = {"X-Api-Key": config.ONEC_API_KEY or ""}
            payload = {"code": code, "telegram_id": telegram_id}
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                if resp.status == 200:
                    await send_clean(message, "Аккаунты успешно связаны! Теперь вы можете входить и через Telegram, и через email.")
                else:
                    detail = data.get("detail", "Неизвестная ошибка")
                    await send_clean(message, f"Ошибка: {detail}")
    except Exception as e:
        logger.exception("Error in /link command: %s", e)
        await send_clean(message, "Произошла ошибка. Попробуйте позже.")


@dp.callback_query(lambda c: c.data and c.data.startswith(OPEN_CALLBACK_PREFIX))
async def newsletter_open_callback(callback: CallbackQuery):
    data = callback.data or ""
    if len(data) > 64:
        logger.warning("Received oversized callback payload: %s", data)
        return await callback.answer("Некорректный запрос", show_alert=True)

    token = data[len(OPEN_CALLBACK_PREFIX) :]
    if not TOKEN_RE.fullmatch(token):
        logger.warning("Invalid newsletter token: %s", data)
        return await callback.answer("Некорректный токен", show_alert=True)

    result, newly_opened = await register_newsletter_open(
        token,
        callback.from_user.id,
        data,
    )

    if not result:
        logger.warning(
            "Newsletter delivery not found for token %s (user=%s)",
            token,
            callback.from_user.id,
        )
        return await callback.answer("Сообщение не найдено", show_alert=True)

    if newly_opened:
        try:
            await callback.message.edit_text(result["message_text"])
        except TelegramBadRequest as exc:
            logger.warning(
                "Failed to edit newsletter message %s: %s",
                result["delivery_id"],
                exc,
            )
            await callback.message.answer(result["message_text"])
        await callback.answer("Сообщение открыто")
    else:
        await callback.answer("Уже открыто")




async def main():
    global bot
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not configured; Telegram bot will not start")
        raise SystemExit(1)
    asyncio.run(main())
