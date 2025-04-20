from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_qr_code_button() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📲 Показать QR-код", callback_data="show_qr")],
            [InlineKeyboardButton(text="💰 Показать бонусы", callback_data="show_bonuses")]
        ]
    )
    return keyboard
