import json
from decimal import Decimal

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

    def test_valid_purchase_returns_201(self):
        response = self._post(self._valid_payload())
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["msg"], "Successfully")
        self.assertTrue(data["is_first_purchase"])
        self.assertEqual(Transaction.objects.count(), 1)

    def test_user_not_found_returns_404(self):
        response = self._post(self._valid_payload(telegram_id=999999))
        self.assertEqual(response.status_code, 404)

    def test_creates_product_if_not_exists(self):
        self.assertFalse(Product.objects.filter(product_code="SKU-001").exists())
        self._post(self._valid_payload())
        self.assertTrue(Product.objects.filter(product_code="SKU-001").exists())

    def test_updates_user_stats(self):
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

    def test_sequential_purchases_accumulate_correctly(self):
        """Two sequential purchases must accumulate total_spent and
        purchase_count correctly thanks to F() expressions."""
        self._post(self._valid_payload(product_code="SKU-001"))
        self._post(self._valid_payload(
            product_code="SKU-002",
            product_name="Product 2",
            total="50.00",
            total_bonuses="25.00",
            bonus_earned="5.00",
        ))
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.total_spent, Decimal("150.00"))
        self.assertEqual(self.customer.purchase_count, 2)
        # bonuses — absolute value from 1C, not accumulated
        self.assertEqual(self.customer.bonuses, Decimal("25.00"))
        self.assertEqual(Transaction.objects.filter(customer=self.customer).count(), 2)
