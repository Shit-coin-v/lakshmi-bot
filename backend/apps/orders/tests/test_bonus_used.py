"""Tests for bonus_used field in order creation."""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase, override_settings

from apps.main.models import CustomUser, Product
from apps.orders.models import DeliveryZone, Order

_TEST_SETTINGS = {
    "CACHES": {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    "ALLOW_TELEGRAM_HEADER_AUTH": True,
}


@override_settings(**_TEST_SETTINGS)
class BonusUsedTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(
            telegram_id=90001,
            bonuses=Decimal("200.00"),
        )
        self.product = Product.objects.create(
            product_code="BNS-1", name="Test Bonus", price="500.00", store_id=1,
        )
        DeliveryZone.objects.all().delete()
        Product.objects.create(
            product_code="DLV-BNS", name="Доставка", price="100.00", store_id=0, is_active=True,
        )
        DeliveryZone.objects.create(name="Тест", product_code="DLV-BNS", is_default=True)

    def _auth(self):
        return {"HTTP_X_TELEGRAM_USER_ID": str(self.customer.telegram_id)}

    def _get_onec_payload(self, order_id):
        """Call send_order_to_onec_impl with mocked HTTP and return the JSON payload."""
        from apps.integrations.onec.order_sync import send_order_to_onec_impl

        fake_self = MagicMock()
        fake_self.request.retries = 0
        fake_self.max_retries = 3

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"onec_guid": "test-guid"}
        mock_resp.text = '{"onec_guid": "test-guid"}'

        with patch("apps.integrations.onec.order_sync.requests.post", return_value=mock_resp) as mock_post, \
             override_settings(ONEC_ORDER_URL="http://fake-1c/order"):
            send_order_to_onec_impl(fake_self, order_id)

        return mock_post.call_args.kwargs.get("json") or mock_post.call_args[1]["json"]

    def _base_payload(self, **overrides):
        payload = {
            "address": "ул. Тестовая, 1",
            "phone": "+79001112233",
            "payment_method": "card_courier",
            "fulfillment_type": "delivery",
            "delivery_zone_code": "DLV-BNS",
            "items": [{"product_code": "BNS-1", "quantity": 2}],
        }
        payload.update(overrides)
        return payload

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_create_order_without_bonus(self, mock_task):
        """Order without bonus_used should default to 0."""
        payload = self._base_payload()
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(id=response.json()["id"])
        self.assertEqual(order.bonus_used, Decimal("0.00"))

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_create_order_with_valid_bonus(self, mock_task):
        """Valid bonus_used within 50% and balance."""
        # total = 500*2 + 100 delivery = 1100, 50% = 550, customer has 200
        payload = self._base_payload(bonus_used="150.00")
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(id=response.json()["id"])
        self.assertEqual(order.bonus_used, Decimal("150.00"))
        self.assertEqual(order.total_price, Decimal("1100.00"))

    def test_bonus_exceeds_50_percent(self):
        """bonus_used > 50% of total should be rejected."""
        # total = 1100, 50% = 550
        self.customer.bonuses = Decimal("600.00")
        self.customer.save(update_fields=["bonuses"])

        payload = self._base_payload(bonus_used="560.00")
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("bonus_used", data)

    def test_bonus_exceeds_balance(self):
        """bonus_used > customer.bonuses should be rejected."""
        # customer has 200, trying to use 250
        payload = self._base_payload(bonus_used="250.00")
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("bonus_used", data)

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_payment_amount_in_detail(self, mock_task):
        """GET order detail should return computed payment_amount."""
        payload = self._base_payload(bonus_used="100.00")
        resp = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        order_id = resp.json()["id"]

        detail = self.client.get(
            f"/api/orders/{order_id}/",
            **self._auth(),
        )
        self.assertEqual(detail.status_code, 200)
        data = detail.json()
        self.assertEqual(data["bonus_used"], "100.00")
        self.assertEqual(data["payment_amount"], "1000.00")  # 1100 - 100

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_onec_payload_contains_bonus(self, mock_task):
        """1C payload should include bonus_used and payment_amount in prices."""
        payload = self._base_payload(bonus_used="100.00")
        self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        order_id = mock_task.call_args[0][0]

        onec_payload = self._get_onec_payload(order_id)
        prices = onec_payload["prices"]
        self.assertEqual(prices["total_price"], "1100.00")
        self.assertEqual(prices["bonus_used"], "100.00")
        self.assertEqual(prices["payment_amount"], "1000.00")

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_balance_not_changed_on_create(self, mock_task):
        """Customer bonuses should NOT change when order is created."""
        original_bonuses = self.customer.bonuses

        payload = self._base_payload(bonus_used="100.00")
        self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.bonuses, original_bonuses)

    @patch("apps.notifications.tasks.send_order_push_task.delay")
    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_balance_not_changed_on_cancel(self, mock_onec, mock_push):
        """Customer bonuses should NOT change when order is canceled."""
        payload = self._base_payload(bonus_used="100.00")
        resp = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        order_id = resp.json()["id"]
        original_bonuses = self.customer.bonuses

        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                f"/api/orders/{order_id}/cancel/",
                content_type="application/json",
                **self._auth(),
            )

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.bonuses, original_bonuses)

    def test_negative_bonus_rejected(self):
        """Negative bonus_used should be rejected."""
        payload = self._base_payload(bonus_used="-10.00")
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(response.status_code, 400)

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_bonus_limit_uses_server_price_not_client(self, mock_task):
        """Anti-cheat: bonus limit must be based on server product price,
        not client-submitted price_at_moment."""
        # Server price = 500, client sends 10 -> total would be 20+100=120 if trusted
        # Server total = 500*2 + 100 = 1100, 50% = 550
        # Client tries bonus_used=200, which is >50% of fake total (120) but <50% of real total (1100)
        self.customer.bonuses = Decimal("200.00")
        self.customer.save(update_fields=["bonuses"])

        payload = self._base_payload(bonus_used="200.00")
        payload["items"] = [{"product_code": "BNS-1", "quantity": 2, "price_at_moment": "10.00"}]
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        # Should succeed because server uses real price (500*2+100=1100, 50%=550, 200<550)
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(id=response.json()["id"])
        # Server prices are used, not client prices
        self.assertEqual(order.products_price, Decimal("1000.00"))
        self.assertEqual(order.total_price, Decimal("1100.00"))
        self.assertEqual(order.bonus_used, Decimal("200.00"))

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_client_fake_low_price_rejected_when_bonus_exceeds_server_50pct(self, mock_task):
        """Anti-cheat: if client sends low price and high bonus_used that exceeds
        50% of real server total, it must be rejected."""
        # Cheap product: server price = 50
        cheap = Product.objects.create(
            product_code="CHEAP-1", name="Cheap", price="50.00", store_id=1,
        )
        self.customer.bonuses = Decimal("200.00")
        self.customer.save(update_fields=["bonuses"])

        # Server total = 50*1 + 100 = 150, 50% = 75
        # Client sends price_at_moment=1000 to inflate perceived total,
        # tries bonus_used=100 which is > 75 (real 50%)
        payload = self._base_payload(bonus_used="100.00")
        payload["items"] = [{"product_code": "CHEAP-1", "quantity": 1, "price_at_moment": "1000.00"}]
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("bonus_used", response.json())

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_create_response_contains_order_id(self, mock_task):
        """Create response should contain order id for the app to fetch details."""
        payload = self._base_payload(bonus_used="50.00")
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("id", data)

        # App then fetches detail — verify bonus fields are there
        detail = self.client.get(
            f"/api/orders/{data['id']}/",
            **self._auth(),
        )
        detail_data = detail.json()
        self.assertEqual(detail_data["bonus_used"], "50.00")
        self.assertEqual(detail_data["payment_amount"], "1050.00")  # 1100 - 50

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_zero_bonus_onec_payload_correct(self, mock_task):
        """With bonus_used=0, 1C payload should have payment_amount = total_price."""
        payload = self._base_payload()
        self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        order_id = mock_task.call_args[0][0]

        onec_payload = self._get_onec_payload(order_id)
        prices = onec_payload["prices"]
        self.assertEqual(prices["total_price"], "1100.00")
        self.assertEqual(prices["bonus_used"], "0.00")
        self.assertEqual(prices["payment_amount"], "1100.00")

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_order_uses_server_price_ignores_client_price(self, mock_task):
        """price_at_moment stored in OrderItem must come from server Product.price."""
        payload = self._base_payload()
        payload["items"] = [{"product_code": "BNS-1", "quantity": 1, "price_at_moment": "1.00"}]
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth(),
        )
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(id=response.json()["id"])
        # Server price is 500, not client's 1.00
        self.assertEqual(order.products_price, Decimal("500.00"))
        self.assertEqual(order.total_price, Decimal("600.00"))
        # OrderItem also stores server price
        item = order.items.first()
        self.assertEqual(item.price_at_moment, Decimal("500.00"))
