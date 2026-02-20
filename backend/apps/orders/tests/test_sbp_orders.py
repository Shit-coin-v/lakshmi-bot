"""Tests for SBP payment flow in order creation and cancellation."""

import json
from unittest.mock import patch

from django.test import Client, TestCase

from apps.main.models import CustomUser, Product
from apps.orders.models import Order

_YUKASSA = "apps.integrations.payments.yukassa_client"


class OrderCreateSBPTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=80001)
        self.product = Product.objects.create(
            product_code="SBP-1", name="Test SBP", price="100.00", store_id=1,
        )

    def _auth(self):
        return {"HTTP_X_TELEGRAM_USER_ID": str(self.customer.telegram_id)}

    @patch(f"{_YUKASSA}.create_payment")
    def test_create_sbp_order_returns_confirmation_url(self, mock_create):
        mock_create.return_value = {
            "payment_id": "pay_sbp_1",
            "confirmation_url": "https://yookassa.ru/pay/123",
            "status": "pending",
        }

        payload = {
            "address": "ул. Тестовая, 1",
            "phone": "+79001112233",
            "payment_method": "sbp",
            "fulfillment_type": "delivery",
            "items": [{"product_code": "SBP-1", "quantity": 2}],
        }
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("confirmation_url", data)
        self.assertEqual(data["confirmation_url"], "https://yookassa.ru/pay/123")
        self.assertIn("payment_id", data)

        order = Order.objects.get(id=data["id"])
        self.assertEqual(order.payment_method, "sbp")
        self.assertEqual(order.payment_status, "pending")
        self.assertEqual(order.payment_id, "pay_sbp_1")

    @patch(f"{_YUKASSA}.create_payment")
    def test_sbp_order_does_not_send_to_onec(self, mock_create):
        """SBP orders should NOT be sent to 1C until payment is authorized."""
        mock_create.return_value = {
            "payment_id": "pay_sbp_2",
            "confirmation_url": "https://yookassa.ru/pay/456",
            "status": "pending",
        }

        with patch("apps.integrations.onec.tasks.send_order_to_onec.delay") as mock_onec:
            payload = {
                "address": "Test",
                "phone": "+79001112233",
                "payment_method": "sbp",
                "items": [{"product_code": "SBP-1", "quantity": 1}],
            }
            self.client.post(
                "/api/orders/create/",
                data=json.dumps(payload),
                content_type="application/json",
                **self._auth(),
            )
            mock_onec.assert_not_called()

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_cash_order_sends_to_onec(self, mock_onec):
        """Non-SBP orders should be sent to 1C immediately."""
        payload = {
            "address": "Test",
            "phone": "+79001112233",
            "payment_method": "cash",
            "items": [{"product_code": "SBP-1", "quantity": 1}],
        }
        self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        mock_onec.assert_called_once()

    @patch(f"{_YUKASSA}.create_payment")
    def test_sbp_payment_failure_cancels_order(self, mock_create):
        mock_create.side_effect = Exception("ЮKassa unavailable")

        payload = {
            "address": "Test",
            "phone": "+79001112233",
            "payment_method": "sbp",
            "items": [{"product_code": "SBP-1", "quantity": 1}],
        }
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(response.status_code, 400)

        order = Order.objects.filter(payment_status="failed").first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "canceled")


class OrderCancelSBPTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=80002)

    def _auth(self):
        return {"HTTP_X_TELEGRAM_USER_ID": str(self.customer.telegram_id)}

    @patch("apps.notifications.tasks.send_order_push_task.delay")
    @patch("apps.integrations.payments.tasks.cancel_payment_task.delay")
    def test_cancel_sbp_order_triggers_payment_cancel(self, mock_cancel, mock_push):
        order = Order.objects.create(
            customer=self.customer,
            address="Test",
            phone="+79001112233",
            payment_method="sbp",
            payment_id="pay_cancel_1",
            payment_status="authorized",
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                f"/api/orders/{order.id}/cancel/", **self._auth(),
            )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, "canceled")
        mock_cancel.assert_called_once_with(order.id)

    @patch("apps.notifications.tasks.send_order_push_task.delay")
    def test_cancel_cash_order_no_payment_cancel(self, mock_push):
        order = Order.objects.create(
            customer=self.customer,
            address="Test",
            phone="+79001112233",
            payment_method="cash",
            payment_status="none",
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                f"/api/orders/{order.id}/cancel/", **self._auth(),
            )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, "canceled")


class SBPSignalTests(TestCase):
    """Test that SBP pending orders don't trigger picker notifications."""

    @patch("apps.notifications.tasks.notify_pickers_new_order.delay")
    def test_sbp_pending_order_no_picker_notification(self, mock_pickers):
        customer = CustomUser.objects.create(telegram_id=80003)

        with self.captureOnCommitCallbacks(execute=True):
            Order.objects.create(
                customer=customer,
                address="Test",
                phone="+79001112233",
                payment_method="sbp",
                payment_status="pending",
            )

        mock_pickers.assert_not_called()

    @patch("apps.notifications.tasks.notify_pickers_new_order.delay")
    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_cash_order_triggers_picker_notification(self, mock_onec, mock_pickers):
        customer = CustomUser.objects.create(telegram_id=80004)

        with self.captureOnCommitCallbacks(execute=True):
            Order.objects.create(
                customer=customer,
                address="Test",
                phone="+79001112233",
                payment_method="cash",
                payment_status="none",
            )

        mock_pickers.assert_called_once()
