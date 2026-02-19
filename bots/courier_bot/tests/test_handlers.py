import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.append(str(Path(__file__).resolve().parents[1]))


# --- Helpers ---

def _make_message(user_id=100, chat_id=1, text=""):
    msg = AsyncMock()
    msg.from_user = SimpleNamespace(id=user_id)
    msg.chat = SimpleNamespace(id=chat_id)
    msg.message_id = 1
    msg.text = text
    msg.bot = AsyncMock()

    sent = AsyncMock()
    sent.message_id = 999
    msg.answer = AsyncMock(return_value=sent)
    msg.delete = AsyncMock()
    return msg


def _make_callback(user_id=100, chat_id=1, data="", message_id=50):
    cb = AsyncMock()
    cb.from_user = SimpleNamespace(id=user_id)
    cb.data = data
    cb.bot = AsyncMock()
    cb.message = AsyncMock()
    cb.message.chat = SimpleNamespace(id=chat_id)
    cb.message.message_id = message_id
    cb.message.edit_text = AsyncMock()
    cb.message.edit_reply_markup = AsyncMock()
    cb.answer = AsyncMock()
    return cb


# Mock approved/denied access results
_APPROVED = {"status": "approved"}
_DENIED = None  # 404 = not registered


# --- /start handler ---

class TestStartHandler:
    @patch("handlers.start.backend.get_courier_profile", new_callable=AsyncMock)
    @patch("handlers.start.backend.check_staff_access", new_callable=AsyncMock)
    @patch("handlers.start.send_clean", new_callable=AsyncMock)
    def test_start_authorized(self, mock_send, mock_check, mock_profile):
        from handlers.start import cmd_start
        mock_check.return_value = _APPROVED
        mock_profile.return_value = {}
        msg = _make_message(user_id=100)
        state = AsyncMock()
        asyncio.run(cmd_start(msg, state))
        mock_send.assert_awaited_once()
        text = mock_send.call_args[0][1]
        assert "Добро пожаловать" in text

    @patch("handlers.start.backend.check_staff_access", new_callable=AsyncMock)
    @patch("handlers.start.send_clean", new_callable=AsyncMock)
    def test_start_not_registered(self, mock_send, mock_check):
        from handlers.start import cmd_start
        mock_check.return_value = _DENIED
        msg = _make_message(user_id=999)
        state = AsyncMock()
        asyncio.run(cmd_start(msg, state))
        mock_send.assert_awaited_once()
        text = mock_send.call_args[0][1]
        assert "ФИО" in text

    @patch("handlers.start.backend.check_staff_access", new_callable=AsyncMock)
    @patch("handlers.start.send_clean", new_callable=AsyncMock)
    def test_start_pending(self, mock_send, mock_check):
        from handlers.start import cmd_start
        mock_check.return_value = {"status": "pending"}
        msg = _make_message(user_id=100)
        state = AsyncMock()
        asyncio.run(cmd_start(msg, state))
        mock_send.assert_awaited_once()
        text = mock_send.call_args[0][1]
        assert "рассмотрении" in text

    @patch("handlers.start.backend.check_staff_access", new_callable=AsyncMock)
    @patch("handlers.start.send_clean", new_callable=AsyncMock)
    def test_start_blacklisted(self, mock_send, mock_check):
        from handlers.start import cmd_start
        mock_check.return_value = {"status": "blacklisted"}
        msg = _make_message(user_id=100)
        state = AsyncMock()
        asyncio.run(cmd_start(msg, state))
        mock_send.assert_awaited_once()
        text = mock_send.call_args[0][1]
        assert "запрещён" in text


# --- /help handler ---

class TestHelpHandler:
    @patch("handlers.help.backend.check_staff_access", new_callable=AsyncMock)
    @patch("handlers.help.send_clean", new_callable=AsyncMock)
    def test_help_authorized(self, mock_send, mock_check):
        from handlers.help import cmd_help
        mock_check.return_value = _APPROVED
        msg = _make_message(user_id=100)
        asyncio.run(cmd_help(msg))
        mock_send.assert_awaited_once()
        text = mock_send.call_args[0][1]
        assert "/orders" in text

    @patch("handlers.help.backend.check_staff_access", new_callable=AsyncMock)
    @patch("handlers.help.send_clean", new_callable=AsyncMock)
    def test_help_unauthorized(self, mock_send, mock_check):
        from handlers.help import cmd_help
        mock_check.return_value = _DENIED
        msg = _make_message(user_id=999)
        asyncio.run(cmd_help(msg))
        text = mock_send.call_args[0][1]
        assert "Доступ запрещён" in text


# --- /orders handler ---

class TestOrdersHandler:
    @patch("handlers.orders._check_access", new_callable=AsyncMock)
    @patch("handlers.orders._cleanup_notifications", new_callable=AsyncMock)
    @patch("handlers.orders._fetch_active_orders", new_callable=AsyncMock)
    @patch("handlers.orders.send_clean", new_callable=AsyncMock)
    def test_orders_authorized(self, mock_send, mock_fetch, mock_cleanup, mock_access):
        from handlers.orders import cmd_orders
        mock_access.return_value = True
        mock_fetch.return_value = []
        msg = _make_message(user_id=100)
        asyncio.run(cmd_orders(msg))
        mock_cleanup.assert_awaited_once()
        mock_fetch.assert_awaited_once()
        mock_send.assert_awaited_once()

    @patch("handlers.orders._check_access", new_callable=AsyncMock)
    @patch("handlers.orders.send_clean", new_callable=AsyncMock)
    def test_orders_unauthorized(self, mock_send, mock_access):
        from handlers.orders import cmd_orders
        mock_access.return_value = False
        msg = _make_message(user_id=999)
        asyncio.run(cmd_orders(msg))
        text = mock_send.call_args[0][1]
        assert "Доступ запрещён" in text


# --- /completed handler ---

class TestCompletedHandler:
    @patch("handlers.orders._check_access", new_callable=AsyncMock)
    @patch("handlers.orders.send_clean", new_callable=AsyncMock)
    @patch("handlers.orders._fetch_completed_today", new_callable=AsyncMock)
    def test_completed_no_orders(self, mock_fetch, mock_send, mock_access):
        from handlers.orders import cmd_completed
        mock_access.return_value = True
        mock_fetch.return_value = 0
        msg = _make_message(user_id=100)
        asyncio.run(cmd_completed(msg))
        mock_send.assert_awaited_once()
        text = mock_send.call_args[0][1]
        assert "пока нет" in text

    @patch("handlers.orders._check_access", new_callable=AsyncMock)
    @patch("handlers.orders.send_clean", new_callable=AsyncMock)
    @patch("handlers.orders._fetch_completed_today", new_callable=AsyncMock)
    def test_completed_with_orders(self, mock_fetch, mock_send, mock_access):
        from handlers.orders import cmd_completed
        mock_access.return_value = True
        mock_fetch.return_value = 5
        msg = _make_message(user_id=100)
        asyncio.run(cmd_completed(msg))
        mock_send.assert_awaited_once()
        text = mock_send.call_args[0][1]
        assert "5" in text
        assert "750" in text  # 5 * 150₽

    @patch("handlers.orders._check_access", new_callable=AsyncMock)
    @patch("handlers.orders.send_clean", new_callable=AsyncMock)
    def test_completed_unauthorized(self, mock_send, mock_access):
        from handlers.orders import cmd_completed
        mock_access.return_value = False
        msg = _make_message(user_id=999)
        asyncio.run(cmd_completed(msg))
        text = mock_send.call_args[0][1]
        assert "Доступ запрещён" in text


# --- Callback: orders_back ---

class TestOrdersBackCallback:
    @patch("handlers.orders._check_access", new_callable=AsyncMock)
    @patch("handlers.orders._fetch_active_orders", new_callable=AsyncMock)
    def test_orders_back(self, mock_fetch, mock_access):
        from handlers.orders import orders_back
        mock_access.return_value = True
        mock_fetch.return_value = []
        cb = _make_callback(user_id=100, data="orders:back")
        asyncio.run(orders_back(cb))
        cb.message.edit_text.assert_awaited_once()
        cb.answer.assert_awaited_once()

    @patch("handlers.orders._check_access", new_callable=AsyncMock)
    def test_orders_back_unauthorized(self, mock_access):
        from handlers.orders import orders_back
        mock_access.return_value = False
        cb = _make_callback(user_id=999, data="orders:back")
        asyncio.run(orders_back(cb))
        cb.answer.assert_awaited_once()
        assert cb.answer.call_args[1].get("show_alert") is True


# --- Callback: noop ---

class TestNoopCallback:
    def test_noop(self):
        from handlers.orders import noop_callback
        cb = _make_callback(data="noop")
        asyncio.run(noop_callback(cb))
        cb.answer.assert_awaited_once()


# --- Callback: order_detail ---

class TestOrderDetailCallback:
    @patch("handlers.orders._check_access", new_callable=AsyncMock)
    @patch("handlers.orders._fetch_order_with_items", new_callable=AsyncMock)
    def test_order_detail_found(self, mock_fetch, mock_access):
        from handlers.orders import order_detail
        mock_access.return_value = True
        order = SimpleNamespace(
            id=5, status="ready", address="ул. Тест", phone="79001234567",
            comment=None, total_price=500, payment_method="cash",
            items=[],
        )
        mock_fetch.return_value = order
        cb = _make_callback(user_id=100, data="order:5:detail")
        asyncio.run(order_detail(cb))
        cb.message.edit_text.assert_awaited_once()
        cb.answer.assert_awaited_once()

    @patch("handlers.orders._check_access", new_callable=AsyncMock)
    @patch("handlers.orders._fetch_order_with_items", new_callable=AsyncMock)
    def test_order_detail_not_found(self, mock_fetch, mock_access):
        from handlers.orders import order_detail
        mock_access.return_value = True
        mock_fetch.return_value = None
        cb = _make_callback(user_id=100, data="order:999:detail")
        asyncio.run(order_detail(cb))
        cb.answer.assert_awaited_once()
        assert cb.answer.call_args[1].get("show_alert") is True

    @patch("handlers.orders._check_access", new_callable=AsyncMock)
    def test_order_detail_unauthorized(self, mock_access):
        from handlers.orders import order_detail
        mock_access.return_value = False
        cb = _make_callback(user_id=999, data="order:5:detail")
        asyncio.run(order_detail(cb))
        cb.answer.assert_awaited_once()
        assert "Доступ запрещён" in cb.answer.call_args[0][0]


# --- Callback: order_status_change ---

class TestOrderStatusChange:
    @patch("handlers.orders._check_access", new_callable=AsyncMock)
    @patch("handlers.orders.schedule_retry")
    @patch("handlers.orders.is_in_flight", return_value=False)
    @patch("handlers.orders._fetch_order_with_items", new_callable=AsyncMock)
    def test_pickup_success(self, mock_fetch, mock_flight, mock_schedule, mock_access):
        from handlers.orders import order_status_change
        mock_access.return_value = True
        order = SimpleNamespace(id=5, status="ready")
        mock_fetch.return_value = order
        cb = _make_callback(user_id=100, data="order:5:pickup")
        asyncio.run(order_status_change(cb))
        cb.message.edit_reply_markup.assert_awaited_once()
        mock_schedule.assert_called_once()
        assert mock_schedule.call_args[1]["new_status"] == "delivery"

    @patch("handlers.orders._check_access", new_callable=AsyncMock)
    @patch("handlers.orders.is_in_flight", return_value=True)
    def test_rejects_if_in_flight(self, mock_flight, mock_access):
        from handlers.orders import order_status_change
        mock_access.return_value = True
        cb = _make_callback(user_id=100, data="order:5:pickup")
        asyncio.run(order_status_change(cb))
        cb.answer.assert_awaited_once()
        assert "обновляется" in cb.answer.call_args[0][0]

    @patch("handlers.orders._check_access", new_callable=AsyncMock)
    @patch("handlers.orders.is_in_flight", return_value=False)
    @patch("handlers.orders._fetch_order_with_items", new_callable=AsyncMock)
    def test_wrong_status(self, mock_fetch, mock_flight, mock_access):
        from handlers.orders import order_status_change
        mock_access.return_value = True
        order = SimpleNamespace(id=5, status="delivery")
        mock_fetch.return_value = order
        cb = _make_callback(user_id=100, data="order:5:pickup")  # expects ready
        asyncio.run(order_status_change(cb))
        cb.answer.assert_awaited_once()
        assert cb.answer.call_args[1].get("show_alert") is True

    @patch("handlers.orders._check_access", new_callable=AsyncMock)
    def test_unauthorized(self, mock_access):
        from handlers.orders import order_status_change
        mock_access.return_value = False
        cb = _make_callback(user_id=999, data="order:5:pickup")
        asyncio.run(order_status_change(cb))
        cb.answer.assert_awaited_once()
        assert "Доступ запрещён" in cb.answer.call_args[0][0]
