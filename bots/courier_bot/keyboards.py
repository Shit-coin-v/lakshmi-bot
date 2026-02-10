from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="\U0001f4e6 \u041c\u043e\u0438 \u0437\u0430\u043a\u0430\u0437\u044b")],
            [KeyboardButton(text="\u2753 \u041f\u043e\u043c\u043e\u0449\u044c")],
        ],
        resize_keyboard=True,
    )
