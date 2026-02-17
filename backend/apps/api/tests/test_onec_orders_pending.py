from apps.common import security
from apps.main.models import CustomUser, Order, OrderItem, Product
from .base import OneCTestBase


class OneCOrdersPendingTests(OneCTestBase):
    def setUp(self):
        super().setUp()
        self.customer = CustomUser.objects.create(telegram_id=5001)

    def _get(self, params="", **extra):
        url = "/onec/orders/pending"
        if params:
            url += f"?{params}"
        return self.client.get(
            url,
            HTTP_X_API_KEY=security.API_KEY,
            **extra,
        )

    def _create_order(self, **kwargs):
        defaults = {
            "customer": self.customer,
            "status": "new",
            "address": "Test address",
            "phone": "+70001112233",
            "products_price": "100.00",
            "delivery_price": "150.00",
            "total_price": "250.00",
        }
        defaults.update(kwargs)
        return Order.objects.create(**defaults)

    def test_returns_new_orders_and_marks_assembly(self):
        order = self._create_order()
        product = Product.objects.create(
            product_code="P1", name="Test", price="50.00", store_id=1,
        )
        OrderItem.objects.create(
            order=order, product=product, quantity=2, price_at_moment="50.00",
        )

        response = self._get()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["orders"][0]["order_id"], order.id)

        order.refresh_from_db()
        self.assertEqual(order.status, "assembly")

    def test_empty_when_no_new_orders(self):
        self._create_order(status="completed")
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

    def test_limit_param(self):
        self._create_order()
        self._create_order()
        response = self._get("limit=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_invalid_after_returns_400(self):
        response = self._get("after=not-a-date")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "invalid_after")

    def test_missing_api_key_returns_401(self):
        response = self.client.get("/onec/orders/pending")
        self.assertEqual(response.status_code, 401)
