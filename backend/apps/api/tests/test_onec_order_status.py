import json
from unittest.mock import patch

from django.test import Client, TestCase

from apps.common import security
from apps.main.models import CustomUser, Order


class OneCOrderStatusTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=6001)
        self.order = Order.objects.create(
            customer=self.customer,
            status="new",
            address="Test",
            phone="+70001112233",
            products_price="100.00",
            delivery_price="150.00",
            total_price="250.00",
        )

    def _post(self, payload, **extra):
        return self.client.post(
            "/onec/order/status",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=security.API_KEY,
            **extra,
        )

    @patch("apps.notifications.tasks.send_order_push_task.delay")
    def test_update_status(self, mock_notify):
        # new -> accepted is a valid FSM transition
        with self.captureOnCommitCallbacks(execute=True):
            response = self._post({"order_id": self.order.id, "status": "accepted"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["order"]["status"], "accepted")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "accepted")
        mock_notify.assert_called_once()

    @patch("apps.notifications.tasks.send_order_push_task.delay")
    def test_set_onec_guid(self, mock_notify):
        # new -> accepted is valid; also sets onec_guid
        with self.captureOnCommitCallbacks(execute=True):
            response = self._post({
                "order_id": self.order.id,
                "status": "accepted",
                "onec_guid": "GUID-123",
            })
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.onec_guid, "GUID-123")

    def test_missing_order_id_returns_400(self):
        response = self._post({"status": "delivery"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "missing_field")

    def test_invalid_status_returns_400(self):
        response = self._post({"order_id": self.order.id, "status": "unknown"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "invalid_status")

    def test_order_not_found_returns_404(self):
        response = self._post({"order_id": 99999, "status": "delivery"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error_code"], "order_not_found")

    def test_invalid_transition_returns_409(self):
        # new -> delivery is not allowed by FSM
        response = self._post({"order_id": self.order.id, "status": "delivery"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error_code"], "invalid_transition")

    def test_missing_api_key_returns_401(self):
        response = self.client.post(
            "/onec/order/status",
            data=json.dumps({"order_id": self.order.id, "status": "delivery"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
