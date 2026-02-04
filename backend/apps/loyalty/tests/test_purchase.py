import json
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase

from apps.common import security
from apps.main.models import CustomUser, Product, Transaction


class PurchaseAPIViewTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        self.client = Client()
        self.customer = CustomUser.objects.create(
            telegram_id=7001, bonuses=0, total_spent=0, purchase_count=0,
        )

    def _post(self, payload, **extra):
        return self.client.post(
            "/api/purchase/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=security.API_KEY,
            **extra,
        )

    def _valid_payload(self, **overrides):
        data = {
            "telegram_id": self.customer.telegram_id,
            "product_code": "SKU-001",
            "product_name": "Test Product",
            "category": "test",
            "quantity": 1,
            "price": "100.00",
            "total": "100.00",
            "purchase_date": "2025-01-15",
            "purchase_time": "12:30:00",
            "store_id": 1,
            "is_promotional": False,
            "bonus_earned": "10.00",
            "total_bonuses": "10.00",
        }
        data.update(overrides)
        return data

    @patch.object(Transaction.objects, "create")
    @patch.object(Transaction.objects, "filter")
    def test_valid_purchase_returns_201(self, mock_filter, mock_create):
        mock_filter.return_value.exists.return_value = False
        mock_txn = MagicMock(id=1, bonus_earned=10)
        mock_create.return_value = mock_txn

        response = self._post(self._valid_payload())
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["msg"], "Successfully")
        self.assertTrue(data["is_first_purchase"])
        mock_create.assert_called_once()

    def test_user_not_found_returns_404(self):
        response = self._post(self._valid_payload(telegram_id=999999))
        self.assertEqual(response.status_code, 404)

    @patch.object(Transaction.objects, "create")
    @patch.object(Transaction.objects, "filter")
    def test_creates_product_if_not_exists(self, mock_filter, mock_create):
        mock_filter.return_value.exists.return_value = False
        mock_create.return_value = MagicMock(id=1, bonus_earned=10)

        self.assertFalse(Product.objects.filter(product_code="SKU-001").exists())
        self._post(self._valid_payload())
        self.assertTrue(Product.objects.filter(product_code="SKU-001").exists())

    @patch.object(Transaction.objects, "create")
    @patch.object(Transaction.objects, "filter")
    def test_updates_user_stats(self, mock_filter, mock_create):
        mock_filter.return_value.exists.return_value = False
        mock_create.return_value = MagicMock(id=1, bonus_earned=10)

        self._post(self._valid_payload())
        self.customer.refresh_from_db()
        self.assertEqual(float(self.customer.bonuses), 10.0)
        self.assertEqual(float(self.customer.total_spent), 100.0)
        self.assertEqual(self.customer.purchase_count, 1)
        self.assertIsNotNone(self.customer.last_purchase_date)

    def test_missing_api_key_returns_401(self):
        response = self.client.post(
            "/api/purchase/",
            data=json.dumps(self._valid_payload()),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
