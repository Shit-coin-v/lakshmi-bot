import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.append(str(Path(__file__).resolve().parents[1]))

from keyboards import (
    get_orders_list_keyboard,
    get_order_detail_keyboard,
    get_cancel_reasons_keyboard,
    _CANCEL_REASON_LABELS,
    payment_label,
)


def _make_order(id=1, status="ready", total_price=500, phone="79001234567"):
    return SimpleNamespace(id=id, status=status, total_price=total_price, phone=phone)


# --- payment_label ---

def test_payment_label_known():
    assert payment_label("card_courier") == "\U0001f4b3 Картой курьеру"
    assert payment_label("cash") == "\U0001f4b5 Наличными"
    assert payment_label("sbp") == "\U0001f4f1 СБП"


def test_payment_label_unknown():
    assert payment_label("bitcoin") == "bitcoin"


# --- get_orders_list_keyboard ---

def test_orders_list_keyboard_with_orders():
    orders = [_make_order(id=1, status="ready", total_price=500),
              _make_order(id=2, status="delivery", total_price=1200)]
    kb = get_orders_list_keyboard(orders)
    buttons = kb.inline_keyboard

    assert len(buttons) == 2
    assert buttons[0][0].callback_data == "order:1:detail"
    assert buttons[1][0].callback_data == "order:2:detail"
    assert "500" in buttons[0][0].text
    assert "1200" in buttons[1][0].text


def test_orders_list_keyboard_empty():
    kb = get_orders_list_keyboard([])
    buttons = kb.inline_keyboard

    assert len(buttons) == 1
    assert buttons[0][0].callback_data == "noop"
    assert "Нет активных заказов" in buttons[0][0].text


def test_orders_list_keyboard_int_price():
    """Total price 1000.0 should display as 1000, not 1000.0."""
    order = _make_order(total_price=1000.0)
    kb = get_orders_list_keyboard([order])
    text = kb.inline_keyboard[0][0].text
    assert "1000₽" in text
    assert "1000.0" not in text


# --- get_order_detail_keyboard ---

def test_order_detail_keyboard_ready():
    order = _make_order(status="ready")
    kb = get_order_detail_keyboard(order)
    data = [btn.callback_data for row in kb.inline_keyboard for btn in row]

    assert "order:1:pickup" in data
    assert "order:1:reassign" in data
    assert "orders:back" in data
    assert "order:1:arrived" not in data
    assert "order:1:complete" not in data


def test_order_detail_keyboard_delivery():
    order = _make_order(status="delivery")
    kb = get_order_detail_keyboard(order)
    data = [btn.callback_data for row in kb.inline_keyboard for btn in row]

    assert "order:1:arrived" in data
    assert "order:1:pickup" not in data


def test_order_detail_keyboard_arrived():
    order = _make_order(status="arrived")
    kb = get_order_detail_keyboard(order)
    data = [btn.callback_data for row in kb.inline_keyboard for btn in row]

    assert "order:1:complete" in data
    assert "order:1:arrived" not in data



def test_order_detail_keyboard_back_always_last():
    for status in ("ready", "delivery", "arrived"):
        order = _make_order(status=status)
        kb = get_order_detail_keyboard(order)
        last_row = kb.inline_keyboard[-1]
        assert last_row[0].callback_data == "orders:back"


# --- Cancel button visibility ---

def test_order_detail_cancel_button_delivery():
    order = _make_order(status="delivery")
    kb = get_order_detail_keyboard(order)
    data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "order:1:cancel" in data


def test_order_detail_cancel_button_arrived():
    order = _make_order(status="arrived")
    kb = get_order_detail_keyboard(order)
    data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "order:1:cancel" in data


def test_order_detail_no_cancel_button_ready():
    order = _make_order(status="ready")
    kb = get_order_detail_keyboard(order)
    data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "order:1:cancel" not in data


# --- get_cancel_reasons_keyboard ---

def test_cancel_reasons_keyboard_has_all_reasons():
    kb = get_cancel_reasons_keyboard(order_id=10)
    data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "order:10:cancelreason:client_refused" in data
    assert "order:10:cancelreason:client_absent" in data
    assert "order:10:cancelreason:long_wait" in data
    assert "order:10:cancelreason:damaged" in data
    assert "order:10:cancelreason:other" in data


def test_cancel_reasons_keyboard_has_back_button():
    kb = get_cancel_reasons_keyboard(order_id=10)
    last_row = kb.inline_keyboard[-1]
    assert last_row[0].callback_data == "order:10:detail"


def test_cancel_reason_labels_long_wait():
    assert "long_wait" in _CANCEL_REASON_LABELS
    assert "долго ждал" in _CANCEL_REASON_LABELS["long_wait"]
