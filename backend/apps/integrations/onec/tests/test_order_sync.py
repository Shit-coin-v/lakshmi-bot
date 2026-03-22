"""Tests for order_sync.py — sending orders to 1C."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.main.models import CustomUser, Product
from apps.orders.models import Order, OrderItem
from apps.integrations.onec.order_sync import (
    _fail_order,
    _get_onec_order_url,
    send_order_to_onec_impl,
)


_TEST_SETTINGS = {
    "CACHES": {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    "CELERY_TASK_ALWAYS_EAGER": True,
}


def _make_celery_self(retries=0, max_retries=5):
    """Create a mock Celery task self with request.retries."""
    mock_self = MagicMock()
    mock_self.request.retries = retries
    mock_self.max_retries = max_retries
    return mock_self


@override_settings(**_TEST_SETTINGS)
class GetOnecOrderUrlTests(TestCase):
    def test_returns_none_when_not_configured(self):
        with self.settings(ONEC_ORDER_URL=None, ONEC_CUSTOMER_URL=None):
            self.assertIsNone(_get_onec_order_url())

    def test_returns_none_when_change_me(self):
        with self.settings(ONEC_ORDER_URL="CHANGE_ME_LATER"):
            self.assertIsNone(_get_onec_order_url())

    def test_returns_url_when_configured(self):
        with self.settings(ONEC_ORDER_URL="http://1c.local/orders"):
            self.assertEqual(_get_onec_order_url(), "http://1c.local/orders")

    def test_falls_back_to_customer_url(self):
        with self.settings(ONEC_ORDER_URL=None, ONEC_CUSTOMER_URL="http://1c.local/customer"):
            self.assertEqual(_get_onec_order_url(), "http://1c.local/customer")


@override_settings(**_TEST_SETTINGS)
class FailOrderTests(TestCase):
    def setUp(self):
        self.customer = CustomUser.objects.create(telegram_id=90001)
        self.order = Order.objects.create(
            customer=self.customer, address="test", phone="+7900",
            total_price=100, products_price=100,
        )

    def test_sets_sync_status_failed(self):
        _fail_order(self.order.id, "some error")
        self.order.refresh_from_db()
        self.assertEqual(self.order.sync_status, "failed")
        self.assertEqual(self.order.last_sync_error, "some error")

    def test_truncates_long_error(self):
        _fail_order(self.order.id, "x" * 5000)
        self.order.refresh_from_db()
        self.assertEqual(len(self.order.last_sync_error), 4000)


@override_settings(**_TEST_SETTINGS)
class SendOrderToOnecImplTests(TestCase):
    def setUp(self):
        self.customer = CustomUser.objects.create(
            telegram_id=90002, email="t@t.com", full_name="Test User",
        )
        self.product = Product.objects.create(
            product_code="P1", name="Товар", price="50.00", store_id=1, is_active=True,
        )
        self.order = Order.objects.create(
            customer=self.customer, address="ул. Тест", phone="+79001112233",
            total_price=100, products_price=100, delivery_price=0,
            payment_method="card_courier", fulfillment_type="delivery",
        )
        OrderItem.objects.create(
            order=self.order, product=self.product,
            quantity=2, price_at_moment=Decimal("50.00"),
        )

    def test_idempotent_already_sent(self):
        """If order already sent, return immediately without HTTP call."""
        from datetime import datetime
        self.order.sync_status = "sent"
        self.order.sent_to_onec_at = datetime(2025, 1, 1, 0, 0, 0)
        self.order.save(update_fields=["sync_status", "sent_to_onec_at"])

        mock_self = _make_celery_self()
        result = send_order_to_onec_impl(mock_self, self.order.id)
        self.assertEqual(result["status"], "already_sent")

    @patch("apps.integrations.onec.order_sync._get_onec_order_url", return_value=None)
    def test_skipped_when_url_not_configured(self, _mock_url):
        mock_self = _make_celery_self()
        result = send_order_to_onec_impl(mock_self, self.order.id)
        self.assertEqual(result["status"], "skipped")

    @patch("apps.integrations.onec.order_sync.requests.post")
    @patch("apps.integrations.onec.order_sync._get_onec_order_url", return_value="http://1c.local/orders")
    def test_successful_send(self, _mock_url, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"onec_guid": "abc-123"}'
        mock_resp.json.return_value = {"onec_guid": "abc-123"}
        mock_post.return_value = mock_resp

        mock_self = _make_celery_self()
        result = send_order_to_onec_impl(mock_self, self.order.id)

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["onec_guid"], "abc-123")

        # Verify order updated in DB
        self.order.refresh_from_db()
        self.assertEqual(self.order.sync_status, "sent")
        self.assertEqual(self.order.onec_guid, "abc-123")
        self.assertIsNotNone(self.order.sent_to_onec_at)

    @patch("apps.integrations.onec.order_sync.requests.post")
    @patch("apps.integrations.onec.order_sync._get_onec_order_url", return_value="http://1c.local/orders")
    def test_extracts_order_guid_fallback(self, _mock_url, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"order_guid": "guid-456"}'
        mock_resp.json.return_value = {"order_guid": "guid-456"}
        mock_post.return_value = mock_resp

        result = send_order_to_onec_impl(_make_celery_self(), self.order.id)
        self.assertEqual(result["onec_guid"], "guid-456")

    @patch("apps.integrations.onec.order_sync.requests.post")
    @patch("apps.integrations.onec.order_sync._get_onec_order_url", return_value="http://1c.local/orders")
    def test_non_json_response_still_succeeds(self, _mock_url, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "OK"
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_post.return_value = mock_resp

        result = send_order_to_onec_impl(_make_celery_self(), self.order.id)
        self.assertEqual(result["status"], "sent")
        self.assertIsNone(result["onec_guid"])

    @patch("apps.integrations.onec.order_sync.requests.post")
    @patch("apps.integrations.onec.order_sync._get_onec_order_url", return_value="http://1c.local/orders")
    def test_payload_structure(self, _mock_url, mock_post):
        """Verify the payload sent to 1C contains expected fields."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "{}"
        mock_resp.json.return_value = {}
        mock_post.return_value = mock_resp

        send_order_to_onec_impl(_make_celery_self(), self.order.id)

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")

        self.assertEqual(payload["order_id"], self.order.id)
        self.assertEqual(payload["customer"]["telegram_id"], 90002)
        self.assertEqual(payload["customer"]["email"], "t@t.com")
        self.assertEqual(payload["store_id"], 1)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["product_code"], "P1")
        self.assertEqual(payload["items"][0]["quantity"], 2)
        self.assertEqual(payload["items"][0]["price"], "50.00")

    @patch("apps.integrations.onec.order_sync.requests.post")
    @patch("apps.integrations.onec.order_sync._get_onec_order_url", return_value="http://1c.local/orders")
    def test_idempotency_key_in_headers(self, _mock_url, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "{}"
        mock_resp.json.return_value = {}
        mock_post.return_value = mock_resp

        send_order_to_onec_impl(_make_celery_self(), self.order.id)

        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        self.assertIn("X-Idempotency-Key", headers)
        self.assertTrue(len(headers["X-Idempotency-Key"]) > 10)

    @patch("apps.integrations.onec.order_sync.requests.post")
    @patch("apps.integrations.onec.order_sync._get_onec_order_url", return_value="http://1c.local/orders")
    def test_http_5xx_returns_failed_in_eager_mode(self, _mock_url, mock_post):
        """In CELERY_TASK_ALWAYS_EAGER mode, 5xx errors return failed status."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        result = send_order_to_onec_impl(_make_celery_self(), self.order.id)
        self.assertEqual(result["status"], "failed")
        self.assertIn("500", result["reason"])

    @patch("apps.integrations.onec.order_sync.requests.post")
    @patch("apps.integrations.onec.order_sync._get_onec_order_url", return_value="http://1c.local/orders")
    def test_sync_attempts_incremented(self, _mock_url, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "{}"
        mock_resp.json.return_value = {}
        mock_post.return_value = mock_resp

        send_order_to_onec_impl(_make_celery_self(), self.order.id)
        self.order.refresh_from_db()
        self.assertEqual(self.order.sync_attempts, 1)

    def test_multiple_store_ids_raises(self):
        """Order with items from different stores should raise RuntimeError."""
        product2 = Product.objects.create(
            product_code="P2", name="Товар 2", price="30.00", store_id=2, is_active=True,
        )
        OrderItem.objects.create(
            order=self.order, product=product2,
            quantity=1, price_at_moment=Decimal("30.00"),
        )

        with self.assertRaises(RuntimeError) as ctx:
            send_order_to_onec_impl(_make_celery_self(), self.order.id)

        self.assertIn("multiple store_id", str(ctx.exception))

    @patch("apps.integrations.onec.order_sync.requests.post")
    @patch("apps.integrations.onec.order_sync._get_onec_order_url", return_value="http://1c.local/orders")
    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    def test_max_retries_exceeded_marks_failed(self, _mock_url, mock_post):
        """When max retries exhausted, order should be marked as failed."""
        import requests as req
        mock_post.side_effect = req.ConnectionError("connection refused")

        mock_self = _make_celery_self(retries=5, max_retries=5)
        result = send_order_to_onec_impl(mock_self, self.order.id)

        self.assertEqual(result["status"], "failed")
        self.order.refresh_from_db()
        self.assertEqual(self.order.sync_status, "failed")

    @patch("apps.integrations.onec.order_sync.requests.post")
    @patch("apps.integrations.onec.order_sync._get_onec_order_url", return_value="http://1c.local/orders")
    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    def test_retry_raised_on_transient_error(self, _mock_url, mock_post):
        """On transient error with retries remaining, should call self.retry()."""
        import requests as req
        mock_post.side_effect = req.ConnectionError("connection refused")

        mock_self = _make_celery_self(retries=0, max_retries=5)
        mock_self.retry.side_effect = Exception("retry-called")

        with self.assertRaises(Exception) as ctx:
            send_order_to_onec_impl(mock_self, self.order.id)

        self.assertEqual(str(ctx.exception), "retry-called")
        mock_self.retry.assert_called_once()
