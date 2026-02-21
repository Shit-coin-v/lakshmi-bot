"""Tests for ЮKassa webhook handler."""

import json
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase

from apps.main.models import CustomUser
from apps.orders.models import Order

# Webhook imports tasks inside the handler function, so mock at source
_TASKS = "apps.notifications.tasks"
_ONEC = "apps.integrations.onec.tasks"
_WEBHOOK = "apps.integrations.payments.webhook"

_WEBHOOK_URL = "/api/payments/webhook/"


class YukassaWebhookIPFilterTests(TestCase):
    """Tests for IP filtering on webhook endpoint."""

    def setUp(self):
        self.client = Client()

    def test_rejected_ip_returns_403(self):
        """Request from non-YooKassa IP should be rejected."""
        payload = {"event": "payment.canceled", "object": {"id": "pay_x"}}
        with patch(f"{_WEBHOOK}._is_yukassa_ip", return_value=False):
            response = self.client.post(
                _WEBHOOK_URL,
                data=json.dumps(payload),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 403)

    def test_allowed_ip_passes(self):
        """Request from YooKassa IP should be accepted."""
        payload = {"event": "payment.succeeded", "object": {"id": "pay_x"}}
        with patch(f"{_WEBHOOK}._is_yukassa_ip", return_value=True):
            response = self.client.post(
                _WEBHOOK_URL,
                data=json.dumps(payload),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)


class YukassaWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=90010)
        self.order = Order.objects.create(
            customer=self.customer,
            address="Test",
            phone="+79001112233",
            total_price=Decimal("500.00"),
            payment_method="sbp",
            payment_id="pay_wh_1",
            payment_status="pending",
        )
        # Bypass IP check for all webhook logic tests
        self._ip_patcher = patch(f"{_WEBHOOK}._is_yukassa_ip", return_value=True)
        self._ip_patcher.start()

    def tearDown(self):
        self._ip_patcher.stop()

    def _post_webhook(self, event, payment_id):
        payload = {"event": event, "object": {"id": payment_id}}
        return self.client.post(
            _WEBHOOK_URL,
            data=json.dumps(payload),
            content_type="application/json",
        )

    @patch(f"{_TASKS}.send_order_push_task.delay")
    @patch(f"{_ONEC}.send_order_to_onec.delay")
    @patch(f"{_TASKS}.notify_pickers_new_order.delay")
    def test_waiting_for_capture_activates_order(self, mock_pickers, mock_onec, mock_push):
        with self.captureOnCommitCallbacks(execute=True):
            response = self._post_webhook("payment.waiting_for_capture", "pay_wh_1")

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "authorized")
        mock_pickers.assert_called_once_with(self.order.id)
        mock_onec.assert_called_once_with(self.order.id)

    @patch(f"{_TASKS}.send_order_push_task.delay")
    def test_payment_canceled_cancels_order(self, mock_push):
        with self.captureOnCommitCallbacks(execute=True):
            response = self._post_webhook("payment.canceled", "pay_wh_1")

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "canceled")
        self.assertEqual(self.order.status, "canceled")

    def test_payment_canceled_does_not_cancel_delivery_order(self):
        """Order in delivery should not be canceled, only payment_status updated."""
        self.order.status = "delivery"
        self.order.payment_status = "authorized"
        self.order.save(update_fields=["status", "payment_status"])

        response = self._post_webhook("payment.canceled", "pay_wh_1")

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "canceled")
        self.assertEqual(self.order.status, "delivery")  # NOT canceled
        self.assertTrue(self.order.manual_check_required)

    def test_unknown_payment_id_returns_200(self):
        response = self._post_webhook("payment.waiting_for_capture", "nonexistent")
        self.assertEqual(response.status_code, 200)

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            _WEBHOOK_URL,
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_payment_id_returns_400(self):
        response = self.client.post(
            _WEBHOOK_URL,
            data=json.dumps({"event": "payment.canceled", "object": {}}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @patch(f"{_TASKS}.send_order_push_task.delay")
    @patch(f"{_ONEC}.send_order_to_onec.delay")
    @patch(f"{_TASKS}.notify_pickers_new_order.delay")
    def test_idempotent_double_authorized(self, mock_pickers, mock_onec, mock_push):
        with self.captureOnCommitCallbacks(execute=True):
            self._post_webhook("payment.waiting_for_capture", "pay_wh_1")

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "authorized")

        # Second call — should be no-op
        mock_pickers.reset_mock()
        mock_onec.reset_mock()

        with self.captureOnCommitCallbacks(execute=True):
            response = self._post_webhook("payment.waiting_for_capture", "pay_wh_1")

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "authorized")
        mock_pickers.assert_not_called()
