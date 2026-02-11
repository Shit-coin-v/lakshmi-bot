from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="\u2753 \u041f\u043e\u043c\u043e\u0449\u044c")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


_STATUS_LABELS = {
    "ready": "\u2705 \u041d\u043e\u0432\u044b\u0439 \u0437\u0430\u043a\u0430\u0437",
    "delivery": "\U0001f697 \u0412 \u043f\u0443\u0442\u0438",
    "arrived": "\U0001f4cd \u041d\u0430 \u043c\u0435\u0441\u0442\u0435",
}

_PAYMENT_LABELS = {
    "card_courier": "\U0001f4b3 \u041a\u0430\u0440\u0442\u043e\u0439 \u043a\u0443\u0440\u044c\u0435\u0440\u0443",
    "cash": "\U0001f4b5 \u041d\u0430\u043b\u0438\u0447\u043d\u044b\u043c\u0438",
    "sbp": "\U0001f4f1 \u0421\u0411\u041f",
}


def get_orders_list_keyboard(orders) -> InlineKeyboardMarkup:
    """InlineKeyboard: list of active orders for courier."""
    buttons = []
    for o in orders:
        label = _STATUS_LABELS.get(o.status, o.status)
        total = int(o.total_price) if o.total_price == int(o.total_price) else o.total_price
        text = f"#{o.id} {label} \u2014 {total}\u20bd"
        buttons.append(
            [InlineKeyboardButton(text=text, callback_data=f"order:{o.id}:detail")]
        )
    if not buttons:
        buttons.append(
            [InlineKeyboardButton(text="\u041d\u0435\u0442 \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0445 \u0437\u0430\u043a\u0430\u0437\u043e\u0432", callback_data="noop")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_order_detail_keyboard(order) -> InlineKeyboardMarkup:
    """InlineKeyboard: action buttons for a specific order."""
    buttons = []

    if order.status == "ready":
        buttons.append(
            [InlineKeyboardButton(
                text="\U0001f697 \u0417\u0430\u0431\u0440\u0430\u043b \u0437\u0430\u043a\u0430\u0437",
                callback_data=f"order:{order.id}:pickup",
            )]
        )
    elif order.status == "delivery":
        buttons.append(
            [InlineKeyboardButton(
                text="\U0001f4cd \u042f \u043d\u0430 \u043c\u0435\u0441\u0442\u0435",
                callback_data=f"order:{order.id}:arrived",
            )]
        )
    elif order.status == "arrived":
        buttons.append(
            [InlineKeyboardButton(
                text="\u2705 \u0414\u043e\u0441\u0442\u0430\u0432\u043b\u0435\u043d\u043e",
                callback_data=f"order:{order.id}:complete",
            )]
        )

    if order.phone:
        buttons.append(
            [InlineKeyboardButton(
                text=f"\U0001f4de {order.phone}",
                callback_data=f"order:{order.id}:phone",
            )]
        )

    buttons.append(
        [InlineKeyboardButton(
            text="\u2b05 \u041d\u0430\u0437\u0430\u0434",
            callback_data="orders:back",
        )]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_label(method: str) -> str:
    return _PAYMENT_LABELS.get(method, method)
