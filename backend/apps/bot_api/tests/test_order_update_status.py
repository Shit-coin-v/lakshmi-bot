import json
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase

from apps.common import permissions, security
from apps.main.models import CustomUser
from apps.orders.models import Order


class OrderUpdateStatusViewTests(TestCase):
    API_KEY = "test-key"

    def setUp(self):
        security.API_KEY = self.API_KEY
        permissions.API_KEY = self.API_KEY
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=8001)
        self.order = Order.objects.create(
            customer=self.customer,
            status="new",
            address="Test",
            phone="+70001112233",
            products_price=Decimal("100"),
            delivery_price=Decimal("150"),
            total_price=Decimal("250"),
        )

    def _post(self, pk, payload):
        return self.client.post(
            f"/api/bot/orders/{pk}/update-status/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=self.API_KEY,
        )

    @patch("apps.notifications.tasks.send_order_push_task.delay")
    def test_valid_transition(self, mock_push):
        with self.captureOnCommitCallbacks(execute=True):
            resp = self._post(self.order.pk, {"status": "accepted", "assembler_id": 12345})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["new_status"], "accepted")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "accepted")
        self.assertEqual(self.order.assembled_by, 12345)
        mock_push.assert_called_once()

    def test_invalid_transition_returns_409(self):
        resp = self._post(self.order.pk, {"status": "delivery"})
        self.assertEqual(resp.status_code, 409)

    def test_order_not_found_returns_404(self):
        resp = self._post(99999, {"status": "accepted"})
        self.assertEqual(resp.status_code, 404)

    def test_missing_status_returns_400(self):
        resp = self._post(self.order.pk, {})
        self.assertEqual(resp.status_code, 400)

    def test_invalid_status_returns_400(self):
        resp = self._post(self.order.pk, {"status": "nonexistent"})
        self.assertEqual(resp.status_code, 400)

    def test_missing_api_key_returns_403(self):
        resp = self.client.post(
            f"/api/bot/orders/{self.order.pk}/update-status/",
            data=json.dumps({"status": "accepted"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    @patch("apps.notifications.tasks.send_order_push_task.delay")
    def test_already_accepted_returns_409(self, mock_push):
        self.order.status = "new"
        self.order.assembled_by = 99999
        self.order.save(update_fields=["status", "assembled_by"])

        # Different assembler tries to accept
        resp = self._post(self.order.pk, {"status": "accepted", "assembler_id": 11111})
        self.assertEqual(resp.status_code, 409)

    def test_invalid_assembler_id_returns_400(self):
        resp = self._post(self.order.pk, {"status": "accepted", "assembler_id": "abc"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "Invalid assembler_id.")

    def test_invalid_courier_id_returns_400(self):
        resp = self._post(self.order.pk, {"status": "accepted", "courier_id": "abc"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "Invalid courier_id.")
