"""Tests for notifications/push.py — FCM push notification logic."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.main.models import CustomUser
from apps.notifications.models import CustomerDevice, Notification
from apps.notifications.push import (
    _send_to_tokens,
    _order_tokens,
    notify_order_status_change,
    notify_notification_created,
)


_TEST_SETTINGS = {
    "CACHES": {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
}


class SendToTokensTests(TestCase):
    """Test _send_to_tokens without real Firebase."""

    @patch("apps.notifications.push.messaging")
    def test_empty_tokens(self, mock_messaging):
        result = _send_to_tokens([], title="T", body="B")
        self.assertEqual(result["sent"], 0)
        self.assertEqual(result["success"], 0)
        mock_messaging.send.assert_not_called()

    @patch("apps.notifications.push.messaging")
    def test_filters_empty_strings(self, mock_messaging):
        result = _send_to_tokens(["", None, ""], title="T", body="B")
        self.assertEqual(result["sent"], 0)
        mock_messaging.send.assert_not_called()

    @patch("apps.notifications.push.messaging")
    def test_single_token_success(self, mock_messaging):
        mock_messaging.send.return_value = "projects/x/messages/123"

        result = _send_to_tokens(["tok1"], title="Title", body="Body", data={"key": 1})
        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["success"], 1)
        self.assertEqual(result["failure"], 0)
        self.assertEqual(result["invalid_tokens"], [])

        mock_messaging.Message.assert_called_once()
        call_kwargs = mock_messaging.Message.call_args
        self.assertEqual(call_kwargs.kwargs["token"], "tok1")

    @patch("apps.notifications.push.messaging")
    def test_multiple_tokens_partial_failure(self, mock_messaging):
        exc = Exception("fail")
        exc.code = "internal-error"
        mock_messaging.send.side_effect = [
            "ok",
            exc,
            "ok",
        ]

        result = _send_to_tokens(["t1", "t2", "t3"], title="T", body="B")
        self.assertEqual(result["sent"], 3)
        self.assertEqual(result["success"], 2)
        self.assertEqual(result["failure"], 1)
        self.assertEqual(result["invalid_tokens"], [])

    @patch("apps.notifications.push.messaging")
    def test_invalid_token_detected(self, mock_messaging):
        exc = Exception("not registered")
        exc.code = "registration-token-not-registered"
        mock_messaging.send.side_effect = exc

        result = _send_to_tokens(["dead-token"], title="T", body="B")
        self.assertEqual(result["failure"], 1)
        self.assertIn("dead-token", result["invalid_tokens"])

    @patch("apps.notifications.push.messaging")
    def test_invalid_argument_token(self, mock_messaging):
        exc = Exception("invalid")
        exc.code = "invalid-argument"
        mock_messaging.send.side_effect = exc

        result = _send_to_tokens(["bad-token"], title="T", body="B")
        self.assertIn("bad-token", result["invalid_tokens"])

    @patch("apps.notifications.push.messaging")
    def test_data_values_converted_to_strings(self, mock_messaging):
        mock_messaging.send.return_value = "ok"
        _send_to_tokens(["tok"], title="T", body="B", data={"num": 42, "flag": True})

        call_kwargs = mock_messaging.Message.call_args
        data = call_kwargs.kwargs.get("data") or call_kwargs[1].get("data")
        self.assertEqual(data, {"num": "42", "flag": "True"})


@override_settings(**_TEST_SETTINGS)
class OrderTokensTests(TestCase):
    def test_returns_tokens_for_customer(self):
        customer = CustomUser.objects.create(telegram_id=70001)
        CustomerDevice.objects.create(customer=customer, fcm_token="tok-a")
        CustomerDevice.objects.create(customer=customer, fcm_token="tok-b")

        order = MagicMock()
        order.customer = customer
        tokens = _order_tokens(order)
        self.assertEqual(sorted(tokens), ["tok-a", "tok-b"])

    def test_returns_empty_when_no_customer(self):
        order = MagicMock(spec=[])  # no customer attr
        tokens = _order_tokens(order)
        self.assertEqual(list(tokens), [])


@override_settings(**_TEST_SETTINGS)
class NotifyOrderStatusChangeTests(TestCase):
    def setUp(self):
        self.customer = CustomUser.objects.create(telegram_id=70010, full_name="Test")
        CustomerDevice.objects.create(customer=self.customer, fcm_token="tok-1")

    def _make_order(self, status="new", fulfillment_type="delivery"):
        from apps.orders.models import Order
        return Order.objects.create(
            customer=self.customer, address="test", phone="+7900",
            total_price=100, products_price=100, status=status,
            fulfillment_type=fulfillment_type,
        )

    def test_same_status_no_notification(self):
        order = self._make_order(status="new")
        # Should return without creating notification
        notify_order_status_change(order, previous_status="new", new_status="new")
        self.assertEqual(Notification.objects.count(), 0)

    def test_unknown_status_no_notification(self):
        order = self._make_order(status="new")
        notify_order_status_change(order, previous_status="new", new_status="unknown_status")
        self.assertEqual(Notification.objects.count(), 0)

    @patch("apps.notifications.push._get_app")
    @patch("apps.notifications.push._send_to_tokens")
    def test_creates_notification_record(self, mock_send, mock_app):
        mock_send.return_value = {"sent": 1, "success": 1, "failure": 0, "invalid_tokens": []}
        order = self._make_order(status="delivery")

        notify_order_status_change(order, previous_status="ready", new_status="delivery")

        notif = Notification.objects.first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.title, "Статус заказа")
        self.assertIn("Курьер забрал", notif.body)

    @patch("apps.notifications.push._get_app")
    @patch("apps.notifications.push._send_to_tokens")
    def test_pickup_ready_message(self, mock_send, mock_app):
        mock_send.return_value = {"sent": 1, "success": 1, "failure": 0, "invalid_tokens": []}
        order = self._make_order(status="ready", fulfillment_type="pickup")

        notify_order_status_change(order, previous_status="assembly", new_status="ready")

        notif = Notification.objects.first()
        self.assertIn("можете забрать", notif.body)

    @patch("apps.notifications.push._get_app")
    @patch("apps.notifications.push._send_to_tokens")
    def test_invalid_tokens_cleaned_up(self, mock_send, mock_app):
        mock_send.return_value = {
            "sent": 1, "success": 0, "failure": 1,
            "invalid_tokens": ["tok-1"],
        }
        order = self._make_order(status="delivery")

        notify_order_status_change(order, previous_status="ready", new_status="delivery")

        self.assertEqual(CustomerDevice.objects.filter(fcm_token="tok-1").count(), 0)

    def test_disabled_order_status_notifications(self):
        self.customer.order_status_enabled = False
        self.customer.save(update_fields=["order_status_enabled"])

        order = self._make_order(status="delivery")
        notify_order_status_change(order, previous_status="ready", new_status="delivery")
        self.assertEqual(Notification.objects.count(), 0)

    @patch("apps.notifications.push._get_app")
    @patch("apps.notifications.push._send_to_tokens")
    def test_no_tokens_still_creates_notification(self, mock_send, mock_app):
        CustomerDevice.objects.all().delete()
        order = self._make_order(status="delivery")

        notify_order_status_change(order, previous_status="ready", new_status="delivery")

        # Notification record created, but no push sent
        self.assertEqual(Notification.objects.count(), 1)
        mock_send.assert_not_called()


@override_settings(**_TEST_SETTINGS)
class NotifyNotificationCreatedTests(TestCase):
    @patch("apps.notifications.push._get_app")
    @patch("apps.notifications.push._send_to_tokens")
    def test_sends_to_user_devices(self, mock_send, mock_app):
        customer = CustomUser.objects.create(telegram_id=70020)
        CustomerDevice.objects.create(customer=customer, fcm_token="tok-x")

        notif = Notification.objects.create(
            user=customer, title="Promo", body="Sale!", type="broadcast",
        )

        mock_send.return_value = {"sent": 1, "success": 1, "failure": 0, "invalid_tokens": []}
        result = notify_notification_created(notif)
        self.assertEqual(result["success"], 1)

        call_kwargs = mock_send.call_args
        self.assertEqual(call_kwargs.kwargs["title"], "Promo")
        self.assertEqual(call_kwargs.kwargs["body"], "Sale!")

    @patch("apps.notifications.push._get_app")
    def test_no_tokens_returns_zero(self, mock_app):
        customer = CustomUser.objects.create(telegram_id=70021)
        notif = Notification.objects.create(
            user=customer, title="T", body="B",
        )
        result = notify_notification_created(notif)
        self.assertEqual(result["sent"], 0)
