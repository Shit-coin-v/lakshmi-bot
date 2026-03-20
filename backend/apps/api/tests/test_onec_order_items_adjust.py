import json
from decimal import Decimal
from unittest.mock import patch

from apps.common import security
from apps.main.models import CustomUser, Product
from apps.orders.models import Order, OrderItem, OrderItemChange
from .base import OneCTestBase


@patch("apps.common.security._ip_allowed", return_value=True)
class OneCOrderItemsAdjustTests(OneCTestBase):
    def setUp(self):
        super().setUp()
        from django.conf import settings as django_settings
        django_settings.ONEC_API_KEY = self.API_KEY

        self.customer = CustomUser.objects.create(telegram_id=7001)
        self.product_a = Product.objects.create(
            name="Кола 0.5л", product_code="P-001", price=Decimal("100.00"), store_id=1,
        )
        self.product_b = Product.objects.create(
            name="Молоко 1л", product_code="P-002", price=Decimal("80.00"), store_id=1,
        )
        self.product_c = Product.objects.create(
            name="Хлеб", product_code="P-003", price=Decimal("50.00"), store_id=1,
        )
        self.order = Order.objects.create(
            customer=self.customer,
            status="assembly",
            address="Test",
            phone="+70001112233",
            products_price=Decimal("510.00"),
            delivery_price=Decimal("200.00"),
            total_price=Decimal("710.00"),
        )
        self.item_a = OrderItem.objects.create(
            order=self.order, product=self.product_a,
            quantity=3, price_at_moment=Decimal("100.00"),
        )
        self.item_b = OrderItem.objects.create(
            order=self.order, product=self.product_b,
            quantity=2, price_at_moment=Decimal("80.00"),
        )
        self.item_c = OrderItem.objects.create(
            order=self.order, product=self.product_c,
            quantity=1, price_at_moment=Decimal("50.00"),
        )

    def _post(self, payload, **extra):
        return self.client.post(
            "/onec/order/items/adjust",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=security.API_KEY,
            **extra,
        )

    # --- Success ---

    def test_decrease_quantity(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [{"product_code": "P-001", "quantity": 1}],
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["products_price"], "310.00")  # 1*100 + 2*80 + 1*50
        self.assertEqual(data["total_price"], "510.00")     # 310 + 200 delivery
        self.assertIn("batch_id", data)
        self.assertEqual(len(data["changes"]), 1)
        self.assertEqual(data["changes"][0]["action"], "decreased")
        self.assertEqual(data["changes"][0]["old_quantity"], 3)
        self.assertEqual(data["changes"][0]["new_quantity"], 1)

        self.item_a.refresh_from_db()
        self.assertEqual(self.item_a.quantity, 1)

        self.order.refresh_from_db()
        self.assertEqual(self.order.products_price, Decimal("310.00"))
        self.assertEqual(self.order.total_price, Decimal("510.00"))

    def test_remove_item(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [{"product_code": "P-003", "quantity": 0}],
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["changes"][0]["action"], "removed")
        self.assertFalse(OrderItem.objects.filter(id=self.item_c.id).exists())

        self.order.refresh_from_db()
        self.assertEqual(self.order.products_price, Decimal("460.00"))  # 3*100 + 2*80

    def test_multiple_changes_in_one_request(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [
                {"product_code": "P-001", "quantity": 1},
                {"product_code": "P-002", "quantity": 0},
            ],
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["changes"]), 2)
        # 1*100 + 0*80 + 1*50 = 150
        self.assertEqual(data["products_price"], "150.00")
        self.assertEqual(data["total_price"], "350.00")

        # Audit: both changes share same batch_id
        changes = OrderItemChange.objects.filter(order=self.order)
        self.assertEqual(changes.count(), 2)
        batch_ids = set(changes.values_list("batch_id", flat=True))
        self.assertEqual(len(batch_ids), 1)

    def test_audit_log_created(self, _mock_ip):
        self._post({
            "order_id": self.order.id,
            "items": [{"product_code": "P-001", "quantity": 2}],
        })
        change = OrderItemChange.objects.get(order=self.order)
        self.assertEqual(change.product_code, "P-001")
        self.assertEqual(change.product_name, "Кола 0.5л")
        self.assertEqual(change.old_quantity, 3)
        self.assertEqual(change.new_quantity, 2)
        self.assertEqual(change.price_at_moment, Decimal("100.00"))
        self.assertEqual(change.change_type, "decreased")
        self.assertEqual(change.source, "onec")

    # --- Validation errors ---

    def test_order_not_found_404(self, _mock_ip):
        resp = self._post({
            "order_id": 99999,
            "items": [{"product_code": "P-001", "quantity": 1}],
        })
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error_code"], "order_not_found")

    def test_not_in_assembly_409(self, _mock_ip):
        self.order.status = "ready"
        self.order.save(update_fields=["status"])
        resp = self._post({
            "order_id": self.order.id,
            "items": [{"product_code": "P-001", "quantity": 1}],
        })
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["error_code"], "invalid_status")

    def test_product_not_in_order_400(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [{"product_code": "NONEXISTENT", "quantity": 1}],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "item_not_found")

    def test_quantity_not_decreased_400(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [{"product_code": "P-001", "quantity": 3}],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "invalid_quantity")

    def test_quantity_increased_400(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [{"product_code": "P-001", "quantity": 5}],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "invalid_quantity")

    def test_quantity_negative_400(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [{"product_code": "P-001", "quantity": -1}],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "invalid_quantity")

    def test_duplicate_product_code_400(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [
                {"product_code": "P-001", "quantity": 1},
                {"product_code": "P-001", "quantity": 2},
            ],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "duplicate_product_code")

    def test_remove_all_items_400(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [
                {"product_code": "P-001", "quantity": 0},
                {"product_code": "P-002", "quantity": 0},
                {"product_code": "P-003", "quantity": 0},
            ],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "cannot_remove_all")
        # Items should NOT be modified (all-or-nothing)
        self.assertEqual(OrderItem.objects.filter(order=self.order).count(), 3)

    def test_missing_order_id_400(self, _mock_ip):
        resp = self._post({"items": [{"product_code": "P-001", "quantity": 1}]})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "missing_field")

    def test_order_id_bool_true_400(self, _mock_ip):
        """order_id=true must not silently resolve to order id=1."""
        resp = self._post({
            "order_id": True,
            "items": [{"product_code": "P-001", "quantity": 1}],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "missing_field")

    def test_order_id_bool_false_400(self, _mock_ip):
        resp = self._post({
            "order_id": False,
            "items": [{"product_code": "P-001", "quantity": 1}],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "missing_field")

    def test_order_id_null_400(self, _mock_ip):
        resp = self._post({
            "order_id": None,
            "items": [{"product_code": "P-001", "quantity": 1}],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "missing_field")

    def test_order_id_empty_string_400(self, _mock_ip):
        resp = self._post({
            "order_id": "",
            "items": [{"product_code": "P-001", "quantity": 1}],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "missing_field")

    def test_order_id_string_accepted(self, _mock_ip):
        """String order_id is accepted (consistent with onec_order_status)."""
        resp = self._post({
            "order_id": str(self.order.id),
            "items": [{"product_code": "P-001", "quantity": 1}],
        })
        self.assertEqual(resp.status_code, 200)

    def test_missing_items_400(self, _mock_ip):
        resp = self._post({"order_id": self.order.id})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "missing_field")

    def test_empty_items_400(self, _mock_ip):
        resp = self._post({"order_id": self.order.id, "items": []})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "missing_field")

    def test_items_null_400(self, _mock_ip):
        resp = self._post({"order_id": self.order.id, "items": None})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "missing_field")

    def test_items_dict_400(self, _mock_ip):
        resp = self._post({"order_id": self.order.id, "items": {}})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "missing_field")

    def test_items_string_400(self, _mock_ip):
        resp = self._post({"order_id": self.order.id, "items": "abc"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "missing_field")

    def test_items_int_400(self, _mock_ip):
        resp = self._post({"order_id": self.order.id, "items": 123})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "missing_field")

    def test_missing_api_key_401(self, _mock_ip):
        resp = self.client.post(
            "/onec/order/items/adjust",
            data=json.dumps({"order_id": self.order.id, "items": []}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    # --- Malformed payload ---

    def test_quantity_bool_true_400(self, _mock_ip):
        """bool is subclass of int in Python; quantity=true must be rejected."""
        resp = self._post({
            "order_id": self.order.id,
            "items": [{"product_code": "P-001", "quantity": True}],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "invalid_payload")

    def test_quantity_bool_false_400(self, _mock_ip):
        """quantity=false must not silently remove an item."""
        resp = self._post({
            "order_id": self.order.id,
            "items": [{"product_code": "P-001", "quantity": False}],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "invalid_payload")
        # Item must NOT be deleted
        self.assertTrue(OrderItem.objects.filter(id=self.item_a.id).exists())

    def test_item_missing_product_code_400(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [{"quantity": 1}],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "invalid_payload")

    def test_item_missing_quantity_400(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [{"product_code": "P-001"}],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "invalid_payload")

    def test_item_not_dict_400(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": ["P-001"],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "invalid_payload")

    def test_empty_product_code_400(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [{"product_code": "", "quantity": 1}],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "invalid_payload")

    def test_quantity_string_400(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [{"product_code": "P-001", "quantity": "2"}],
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error_code"], "invalid_payload")

    def test_no_partial_changes_on_error(self, _mock_ip):
        """If second item fails validation, first item must not be modified."""
        resp = self._post({
            "order_id": self.order.id,
            "items": [
                {"product_code": "P-001", "quantity": 1},       # valid
                {"product_code": "P-002", "quantity": 5},       # invalid: > current
            ],
        })
        self.assertEqual(resp.status_code, 400)
        # First item must NOT have been changed
        self.item_a.refresh_from_db()
        self.assertEqual(self.item_a.quantity, 3)

    def test_batch_id_same_for_all_changes(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [
                {"product_code": "P-001", "quantity": 1},
                {"product_code": "P-002", "quantity": 1},
            ],
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        batch_id_from_response = data["batch_id"]
        changes = OrderItemChange.objects.filter(order=self.order)
        self.assertEqual(changes.count(), 2)
        for change in changes:
            self.assertEqual(str(change.batch_id), batch_id_from_response)

    # --- Other ---

    def test_delivery_price_unchanged(self, _mock_ip):
        resp = self._post({
            "order_id": self.order.id,
            "items": [{"product_code": "P-001", "quantity": 1}],
        })
        data = resp.json()
        self.assertEqual(data["delivery_price"], "200.00")
        self.order.refresh_from_db()
        self.assertEqual(self.order.delivery_price, Decimal("200.00"))
