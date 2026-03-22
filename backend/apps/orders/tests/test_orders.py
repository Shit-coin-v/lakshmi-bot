import json
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from apps.main.models import CustomUser, Order, OrderItem, Product
from apps.orders.models import DeliveryZone

_TEST_SETTINGS = {
    "CACHES": {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    "ALLOW_TELEGRAM_HEADER_AUTH": True,
}


@override_settings(**_TEST_SETTINGS)
class ProductListViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_product_list_active_only(self):
        Product.objects.create(
            product_code="A1", name="Active", price="10.00", store_id=1, is_active=True,
        )
        Product.objects.create(
            product_code="A2", name="Inactive", price="20.00", store_id=1, is_active=False,
        )
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        codes = [p["product_code"] for p in data]
        self.assertIn("A1", codes)
        self.assertNotIn("A2", codes)

    def test_product_search(self):
        Product.objects.create(
            product_code="S1", name="Apple Juice", price="5.00", store_id=1,
        )
        Product.objects.create(
            product_code="S2", name="Orange Soda", price="3.00", store_id=1,
        )
        response = self.client.get("/api/products/?search=Apple")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["product_code"], "S1")


@override_settings(**_TEST_SETTINGS)
class OrderCreateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=10001)
        self.product = Product.objects.create(
            product_code="ORD-1", name="Test Product", price="50.00", store_id=1,
        )
        DeliveryZone.objects.all().delete()

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_create_order(self, mock_task):
        Product.objects.create(
            product_code="DLV-1", name="Доставка", price="200.00", store_id=0, is_active=True,
        )
        DeliveryZone.objects.create(
            name="Тест", product_code="DLV-1", is_default=True,
        )
        payload = {
            "customer_id": self.customer.id,
            "address": "ул. Тестовая, 1",
            "phone": "+79001112233",
            "payment_method": "card_courier",
            "fulfillment_type": "delivery",
            "delivery_zone_code": "DLV-1",
            "items": [{"product_code": "ORD-1", "quantity": 2}],
        }
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID=str(self.customer.telegram_id),
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("id", data)
        order = Order.objects.get(id=data["id"])
        self.assertEqual(order.status, "new")
        self.assertEqual(order.delivery_price, Decimal("200.00"))
        self.assertEqual(order.delivery_zone_code, "DLV-1")
        self.assertEqual(float(order.products_price), 100.0)
        mock_task.assert_called_once()

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_create_order_zone_code_trimmed(self, mock_task):
        Product.objects.create(
            product_code="DLV-1", name="Доставка", price="200.00", store_id=0, is_active=True,
        )
        DeliveryZone.objects.create(
            name="Тест", product_code="DLV-1", is_default=True,
        )
        payload = {
            "customer_id": self.customer.id,
            "address": "ул. Тестовая, 1",
            "phone": "+79001112233",
            "payment_method": "card_courier",
            "fulfillment_type": "delivery",
            "delivery_zone_code": "  DLV-1  ",
            "items": [{"product_code": "ORD-1", "quantity": 2}],
        }
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID=str(self.customer.telegram_id),
        )
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(id=response.json()["id"])
        self.assertEqual(order.delivery_zone_code, "DLV-1")

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_create_order_pickup(self, mock_task):
        payload = {
            "customer_id": self.customer.id,
            "address": "Самовывоз",
            "phone": "+79001112233",
            "payment_method": "cash",
            "fulfillment_type": "pickup",
            "items": [{"product_code": "ORD-1", "quantity": 1}],
        }
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID=str(self.customer.telegram_id),
        )
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(id=response.json()["id"])
        self.assertEqual(float(order.delivery_price), 0.0)

    def test_create_order_product_not_found_returns_400(self):
        payload = {
            "customer_id": self.customer.id,
            "address": "Test",
            "phone": "+79001112233",
            "payment_method": "cash",
            "items": [{"product_code": "NONEXISTENT", "quantity": 1}],
        }
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID=str(self.customer.telegram_id),
        )
        self.assertEqual(response.status_code, 400)


@override_settings(**_TEST_SETTINGS)
class OrderListAndDetailTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=10002)
        self.order = Order.objects.create(
            customer=self.customer,
            status="new",
            address="Test",
            phone="+79001112233",
            products_price="50.00",
            delivery_price="150.00",
            total_price="200.00",
        )
        self.product = Product.objects.create(
            product_code="DET-1", name="Detail Product", price="50.00", store_id=1,
        )
        OrderItem.objects.create(
            order=self.order, product=self.product, quantity=1, price_at_moment="50.00",
        )

    def test_order_list_by_user(self):
        response = self.client.get(
            f"/api/orders/?user_id={self.customer.id}",
            HTTP_X_TELEGRAM_USER_ID=str(self.customer.telegram_id),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], self.order.id)

    def test_order_list_without_auth_returns_401(self):
        response = self.client.get("/api/orders/")
        self.assertEqual(response.status_code, 401)

    def test_order_detail(self):
        response = self.client.get(
            f"/api/orders/{self.order.pk}/",
            HTTP_X_TELEGRAM_USER_ID=str(self.customer.telegram_id),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], self.order.id)
        self.assertEqual(len(data["items"]), 1)

    def test_order_not_found_returns_404(self):
        response = self.client.get(
            "/api/orders/99999/",
            HTTP_X_TELEGRAM_USER_ID=str(self.customer.telegram_id),
        )
        self.assertEqual(response.status_code, 404)
