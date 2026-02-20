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

    def _post_webhook(self, event, payment_id):
        payload = {"event": event, "object": {"id": payment_id}}
        return self.client.post(
            "/payments/webhook/",
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

    def test_unknown_payment_id_returns_200(self):
        response = self._post_webhook("payment.waiting_for_capture", "nonexistent")
        self.assertEqual(response.status_code, 200)

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            "/payments/webhook/",
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_payment_id_returns_400(self):
        response = self.client.post(
            "/payments/webhook/",
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
