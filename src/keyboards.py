from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_qr_code_button() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📲 Показать QR-код", callback_data="show_qr")],
            [InlineKeyboardButton(text="💰 Показать бонусы", callback_data="show_bonuses")],
            [InlineKeyboardButton(text="👥 Пригласить друга", callback_data="invite_friend")]
        ]
    )
    return keyboard


def get_consent_button() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Я согласен", callback_data="personal_data_agree")]
        ]
    )
    return keyboard
