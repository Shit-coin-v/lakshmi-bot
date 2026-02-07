from django.test import Client, TestCase

from apps.main.models import CustomUser, Notification, Order, Product


class ProductListPaginationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_returns_pagination_headers(self):
        for i in range(3):
            Product.objects.create(
                product_code=f"P{i}", name=f"Product {i}", price="10.00", store_id=1,
            )
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Total-Count"], "3")
        self.assertEqual(response["X-Page"], "1")
        self.assertIn("X-Page-Size", response)

    def test_body_is_array(self):
        Product.objects.create(
            product_code="PA", name="Array Test", price="5.00", store_id=1,
        )
        response = self.client.get("/api/products/")
        data = response.json()
        self.assertIsInstance(data, list)

    def test_respects_page_size_param(self):
        for i in range(5):
            Product.objects.create(
                product_code=f"PS{i}", name=f"Sized {i}", price="1.00", store_id=1,
            )
        response = self.client.get("/api/products/?page_size=2")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(response["X-Total-Count"], "5")
        self.assertIn("Link", response)
        self.assertIn('rel="next"', response["Link"])

    def test_page_size_max_limit(self):
        Product.objects.create(
            product_code="ML", name="Max Limit", price="1.00", store_id=1,
        )
        response = self.client.get("/api/products/?page_size=999")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Page-Size"], "200")

    def test_second_page(self):
        for i in range(3):
            Product.objects.create(
                product_code=f"PG{i}", name=f"Page {i}", price="1.00", store_id=1,
            )
        response = self.client.get("/api/products/?page_size=2&page=2")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertIn('rel="prev"', response["Link"])


class OrderListPaginationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=90001)

    def _headers(self):
        return {"HTTP_X_TELEGRAM_USER_ID": str(self.customer.telegram_id)}

    def test_returns_pagination_headers(self):
        for i in range(3):
            Order.objects.create(customer=self.customer, total_price="100.00")
        response = self.client.get("/api/orders/", **self._headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Total-Count"], "3")
        self.assertIsInstance(response.json(), list)


class NotificationListPaginationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=90002)

    def _headers(self):
        return {"HTTP_X_TELEGRAM_USER_ID": str(self.customer.telegram_id)}

    def test_returns_pagination_headers(self):
        for i in range(3):
            Notification.objects.create(
                user=self.customer, title=f"N{i}", body="body",
            )
        response = self.client.get("/api/notifications/", **self._headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Total-Count"], "3")
        self.assertIsInstance(response.json(), list)
