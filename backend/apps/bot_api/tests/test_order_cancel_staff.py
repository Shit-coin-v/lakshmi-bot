from unittest.mock import patch

from django.test import Client, TestCase

from apps.common import permissions, security
from apps.main.models import CustomUser
from apps.orders.models import Order


class OrderCancelByStaffTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        permissions.API_KEY = "test-key"
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=90001)
        self.headers = {"HTTP_X_API_KEY": "test-key"}

    def _create_order(self, status="delivery"):
        return Order.objects.create(
            customer=self.customer,
            address="ул. Тестовая, 1",
            phone="+79001112233",
            payment_method="cash",
            status=status,
        )

    @patch("apps.notifications.tasks.send_order_push_task.delay")
    def test_cancel_with_long_wait_reason(self, mock_push):
        order = self._create_order("delivery")
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(
                f"/api/bot/orders/{order.id}/cancel/",
                data={"reason": "long_wait", "role": "courier"},
                content_type="application/json",
                **self.headers,
            )
        self.assertEqual(resp.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, "canceled")
        self.assertEqual(order.cancel_reason, "long_wait")
        self.assertEqual(order.canceled_by, "courier")

    @patch("apps.notifications.tasks.send_order_push_task.delay")
    def test_cancel_with_client_refused_reason(self, mock_push):
        order = self._create_order("arrived")
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(
                f"/api/bot/orders/{order.id}/cancel/",
                data={"reason": "client_refused", "role": "courier"},
                content_type="application/json",
                **self.headers,
            )
        self.assertEqual(resp.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.cancel_reason, "client_refused")

    def test_cancel_with_invalid_reason(self):
        order = self._create_order("delivery")
        resp = self.client.post(
            f"/api/bot/orders/{order.id}/cancel/",
            data={"reason": "bogus_reason", "role": "courier"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, "delivery")

    def test_cancel_completed_rejected(self):
        order = self._create_order("completed")
        resp = self.client.post(
            f"/api/bot/orders/{order.id}/cancel/",
            data={"reason": "other", "role": "courier"},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(resp.status_code, 400)

    def test_cancel_no_api_key(self):
        order = self._create_order("delivery")
        resp = self.client.post(
            f"/api/bot/orders/{order.id}/cancel/",
            data={"reason": "long_wait", "role": "courier"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
