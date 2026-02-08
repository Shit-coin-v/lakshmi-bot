from unittest.mock import patch

from django.test import Client, TestCase

from apps.main.models import CustomUser, Order


class OrderCancelViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=99001)

    def _create_order(self, status="new"):
        order = Order.objects.create(
            customer=self.customer,
            address="ул. Тестовая, 1",
            phone="+79001112233",
            payment_method="cash",
            status=status,
        )
        return order

    def _auth_header(self):
        return {"HTTP_X_TELEGRAM_USER_ID": str(self.customer.telegram_id)}

    @patch("apps.notifications.tasks.send_order_push_task.delay")
    def test_cancel_from_new(self, mock_notify):
        order = self._create_order("new")
        response = self.client.post(f"/api/orders/{order.id}/cancel/", **self._auth_header())
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, "canceled")
        mock_notify.assert_called_once()

    @patch("apps.notifications.tasks.send_order_push_task.delay")
    def test_cancel_from_assembly(self, mock_notify):
        order = self._create_order("assembly")
        response = self.client.post(f"/api/orders/{order.id}/cancel/", **self._auth_header())
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, "canceled")

    def test_cancel_from_delivery_rejected(self):
        order = self._create_order("delivery")
        response = self.client.post(f"/api/orders/{order.id}/cancel/", **self._auth_header())
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, "delivery")

    def test_cancel_from_completed_rejected(self):
        order = self._create_order("completed")
        response = self.client.post(f"/api/orders/{order.id}/cancel/", **self._auth_header())
        self.assertEqual(response.status_code, 400)

    def test_cancel_from_canceled_rejected(self):
        order = self._create_order("canceled")
        response = self.client.post(f"/api/orders/{order.id}/cancel/", **self._auth_header())
        self.assertEqual(response.status_code, 400)

    def test_cancel_nonexistent_order(self):
        response = self.client.post("/api/orders/99999/cancel/", **self._auth_header())
        self.assertEqual(response.status_code, 404)
