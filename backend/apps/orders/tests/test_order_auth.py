import json
from unittest.mock import patch

from django.test import Client, TestCase

from apps.main.models import CustomUser, Order, OrderItem, Product


class OrderCreateAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create(telegram_id=12345)
        self.product = Product.objects.create(
            product_code="AUTH-1", name="Auth Product", price="50.00", store_id=1,
        )

    def _payload(self):
        return {
            "customer_id": self.user.id,
            "address": "ул. Тестовая, 1",
            "phone": "+79001112233",
            "payment_method": "card_courier",
            "fulfillment_type": "delivery",
            "items": [{"product_code": "AUTH-1", "quantity": 1}],
        }

    def test_order_create_without_header_returns_403(self):
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(self._payload()),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_order_create_with_valid_header_returns_201(self, mock_task):
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(self._payload()),
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID=str(self.user.telegram_id),
        )
        self.assertEqual(response.status_code, 201)

    def test_order_create_with_unknown_telegram_id_returns_403(self):
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(self._payload()),
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID="999999999",
        )
        self.assertEqual(response.status_code, 403)

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_order_create_with_other_customer_id_uses_authenticated_user(self, mock_task):
        other_user = CustomUser.objects.create(telegram_id=99999)
        payload = self._payload()
        payload["customer_id"] = other_user.id
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID=str(self.user.telegram_id),
        )
        self.assertEqual(response.status_code, 201)
        order = Order.objects.latest("id")
        self.assertEqual(order.customer, self.user)


class OrderDetailAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create(telegram_id=22001)
        self.other_user = CustomUser.objects.create(telegram_id=22002)
        self.order = Order.objects.create(
            customer=self.user,
            status="new",
            address="Test",
            phone="+79001112233",
            products_price="50.00",
            delivery_price="150.00",
            total_price="200.00",
        )
        self.product = Product.objects.create(
            product_code="DET-A1", name="Detail Product", price="50.00", store_id=1,
        )
        OrderItem.objects.create(
            order=self.order, product=self.product, quantity=1, price_at_moment="50.00",
        )

    def test_order_detail_without_header_returns_403(self):
        response = self.client.get(f"/api/orders/{self.order.pk}/")
        self.assertEqual(response.status_code, 403)

    def test_order_detail_own_order_returns_200(self):
        response = self.client.get(
            f"/api/orders/{self.order.pk}/",
            HTTP_X_TELEGRAM_USER_ID=str(self.user.telegram_id),
        )
        self.assertEqual(response.status_code, 200)

    def test_order_detail_wrong_user_returns_403(self):
        response = self.client.get(
            f"/api/orders/{self.order.pk}/",
            HTTP_X_TELEGRAM_USER_ID=str(self.other_user.telegram_id),
        )
        self.assertEqual(response.status_code, 403)


class OrderListAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create(telegram_id=33001)
        self.other_user = CustomUser.objects.create(telegram_id=33002)
        self.order = Order.objects.create(
            customer=self.user,
            status="new",
            address="Test",
            phone="+79001112233",
            products_price="50.00",
            delivery_price="150.00",
            total_price="200.00",
        )
        Order.objects.create(
            customer=self.other_user,
            status="new",
            address="Test Other",
            phone="+79001112244",
            products_price="30.00",
            delivery_price="150.00",
            total_price="180.00",
        )

    def test_order_list_without_header_returns_403(self):
        response = self.client.get("/api/orders/")
        self.assertEqual(response.status_code, 403)

    def test_order_list_returns_only_own_orders(self):
        response = self.client.get(
            "/api/orders/",
            HTTP_X_TELEGRAM_USER_ID=str(self.user.telegram_id),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], self.order.id)

    def test_order_list_ignores_user_id_param(self):
        """user_id query param should be ignored; only telegram_user matters."""
        response = self.client.get(
            f"/api/orders/?user_id={self.other_user.id}",
            HTTP_X_TELEGRAM_USER_ID=str(self.user.telegram_id),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], self.order.id)


class OrderCancelAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create(telegram_id=44001)
        self.other_user = CustomUser.objects.create(telegram_id=44002)
        self.order = Order.objects.create(
            customer=self.user,
            status="new",
            address="Test",
            phone="+79001112233",
            products_price="50.00",
            delivery_price="150.00",
            total_price="200.00",
        )

    def test_order_cancel_without_header_returns_403(self):
        response = self.client.post(f"/api/orders/{self.order.pk}/cancel/")
        self.assertEqual(response.status_code, 403)

    @patch("apps.notifications.tasks.send_order_push_task.delay")
    def test_order_cancel_own_order_returns_200(self, mock_notify):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                f"/api/orders/{self.order.pk}/cancel/",
                content_type="application/json",
                HTTP_X_TELEGRAM_USER_ID=str(self.user.telegram_id),
            )
        self.assertEqual(response.status_code, 200)

    def test_order_cancel_wrong_user_returns_403(self):
        response = self.client.post(
            f"/api/orders/{self.order.pk}/cancel/",
            HTTP_X_TELEGRAM_USER_ID=str(self.other_user.telegram_id),
        )
        self.assertEqual(response.status_code, 403)


class ProductListNoAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        Product.objects.create(
            product_code="PUB-1", name="Public Product", price="10.00", store_id=1,
        )

    def test_product_list_no_auth_required(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
