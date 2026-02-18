from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)


_FULFILLMENT_LABELS = {
    "delivery": "🚚 Доставка",
    "pickup": "🏪 Самовывоз",
}

_PAYMENT_LABELS = {
    "card_courier": "💳 Картой курьеру",
    "cash": "💵 Наличными",
    "sbp": "📱 СБП",
}


def get_new_orders_keyboard(orders) -> InlineKeyboardMarkup:
    """InlineKeyboard: list of new orders for picker."""
    buttons = []
    for o in orders:
        tp = float(o.total_price)
        total = int(tp) if tp == int(tp) else tp
        fulfillment = "🏪" if o.fulfillment_type == "pickup" else "🚚"
        text = f"#{o.id} 🆕 {fulfillment} — {total}₽"
        buttons.append(
            [InlineKeyboardButton(text=text, callback_data=f"order:{o.id}:detail")]
        )
    if not buttons:
        buttons.append(
            [InlineKeyboardButton(text="Нет новых заказов", callback_data="noop")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_active_orders_keyboard(orders) -> InlineKeyboardMarkup:
    """InlineKeyboard: list of picker's active orders."""
    _status_icons = {
        "accepted": "📋",
        "assembly": "📦",
        "ready": "✅",
    }
    buttons = []
    for o in orders:
        tp = float(o.total_price)
        total = int(tp) if tp == int(tp) else tp
        icon = _status_icons.get(o.status, "📦")
        text = f"#{o.id} {icon} — {total}₽"
        buttons.append(
            [InlineKeyboardButton(text=text, callback_data=f"order:{o.id}:detail")]
        )
    if not buttons:
        buttons.append(
            [InlineKeyboardButton(text="Нет активных заказов", callback_data="noop")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_order_detail_keyboard(order) -> InlineKeyboardMarkup:
    """InlineKeyboard: action buttons depending on order status."""
    buttons = []

    if order.status == "new":
        buttons.append(
            [InlineKeyboardButton(
                text="📋 Принять",
                callback_data=f"order:{order.id}:accept",
            )]
        )
    elif order.status == "accepted":
        buttons.append(
            [InlineKeyboardButton(
                text="📦 Собираем",
                callback_data=f"order:{order.id}:assemble",
            )]
        )
    elif order.status == "assembly":
        buttons.append(
            [InlineKeyboardButton(
                text="✅ Заказ собрал",
                callback_data=f"order:{order.id}:ready",
            )]
        )
    elif order.status == "ready" and order.fulfillment_type == "pickup":
        buttons.append(
            [InlineKeyboardButton(
                text="🤝 Клиент забрал",
                callback_data=f"order:{order.id}:pickup_complete",
            )]
        )

    buttons.append(
        [InlineKeyboardButton(
            text="⬅ Назад",
            callback_data="orders:back",
        )]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_label(method: str) -> str:
    return _PAYMENT_LABELS.get(method, method)


def fulfillment_label(ft: str) -> str:
    return _FULFILLMENT_LABELS.get(ft, ft)
