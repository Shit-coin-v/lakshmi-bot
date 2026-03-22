"""Tests for onec/tasks.py — Celery tasks for 1C notifications and rollback."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.main.models import CustomUser
from apps.orders.models import Order


_TEST_SETTINGS = {
    "CACHES": {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    "CELERY_TASK_ALWAYS_EAGER": True,
    "CELERY_TASK_EAGER_PROPAGATES": True,
}


@override_settings(**_TEST_SETTINGS)
class NotifyOnecOrderCanceledTests(TestCase):
    def setUp(self):
        self.customer = CustomUser.objects.create(telegram_id=80001, email="c@c.com")
        self.order = Order.objects.create(
            customer=self.customer, address="test", phone="+7900",
            total_price=100, products_price=100, status="canceled",
            cancel_reason="client_refused", canceled_by="client",
            payment_method="card_courier",
        )

    @patch("apps.integrations.onec.tasks._get_onec_order_url", return_value=None)
    def test_skipped_when_no_url(self, _mock_url):
        from apps.integrations.onec.tasks import notify_onec_order_canceled
        result = notify_onec_order_canceled.apply(args=[self.order.id]).result
        self.assertEqual(result["status"], "skipped")

    @patch("apps.integrations.onec.tasks.requests.post")
    @patch("apps.integrations.onec.tasks._get_onec_order_url", return_value="http://1c.local/orders")
    def test_successful_cancel_notification(self, _mock_url, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        from apps.integrations.onec.tasks import notify_onec_order_canceled
        result = notify_onec_order_canceled.apply(args=[self.order.id]).result
        self.assertEqual(result["status"], "sent")

        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        self.assertEqual(payload["order_id"], self.order.id)
        self.assertEqual(payload["status"], "canceled")
        self.assertEqual(payload["cancel_reason"], "client_refused")
        self.assertEqual(payload["canceled_by"], "client")

    @patch("apps.integrations.onec.tasks.requests.post")
    @patch("apps.integrations.onec.tasks._get_onec_order_url", return_value="http://1c.local/orders")
    def test_payment_result_no_online_payment(self, _mock_url, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        from apps.integrations.onec.tasks import notify_onec_order_canceled
        notify_onec_order_canceled.apply(args=[self.order.id])

        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        self.assertEqual(payload["payment_result"], "no_online_payment")

    @patch("apps.integrations.onec.tasks.requests.post")
    @patch("apps.integrations.onec.tasks._get_onec_order_url", return_value="http://1c.local/orders")
    def test_payment_result_hold_canceled(self, _mock_url, mock_post):
        self.order.payment_id = "pay-123"
        self.order.payment_status = "canceled"
        self.order.save(update_fields=["payment_id", "payment_status"])

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        from apps.integrations.onec.tasks import notify_onec_order_canceled
        notify_onec_order_canceled.apply(args=[self.order.id])

        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        self.assertEqual(payload["payment_result"], "hold_canceled")

    @patch("apps.integrations.onec.tasks.requests.post")
    @patch("apps.integrations.onec.tasks._get_onec_order_url", return_value="http://1c.local/orders")
    def test_payment_result_refund_pending(self, _mock_url, mock_post):
        self.order.payment_id = "pay-123"
        self.order.payment_status = "authorized"
        self.order.save(update_fields=["payment_id", "payment_status"])

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        from apps.integrations.onec.tasks import notify_onec_order_canceled
        notify_onec_order_canceled.apply(args=[self.order.id])

        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        self.assertEqual(payload["payment_result"], "refund_pending")

    @patch("apps.integrations.onec.tasks._get_onec_order_url", return_value="http://1c.local/orders")
    def test_order_not_found(self, _mock_url):
        from apps.integrations.onec.tasks import notify_onec_order_canceled
        result = notify_onec_order_canceled.apply(args=[999999]).result
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "order_not_found")

    @patch("apps.integrations.onec.tasks.requests.post")
    @patch("apps.integrations.onec.tasks._get_onec_order_url", return_value="http://1c.local/orders")
    def test_http_error_returns_failed_in_eager(self, _mock_url, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Server Error"
        mock_post.return_value = mock_resp

        from apps.integrations.onec.tasks import notify_onec_order_canceled
        result = notify_onec_order_canceled.apply(args=[self.order.id]).result
        self.assertEqual(result["status"], "failed")


@override_settings(**_TEST_SETTINGS)
class NotifyOnecOrderCompletedTests(TestCase):
    def setUp(self):
        self.customer = CustomUser.objects.create(telegram_id=80010)
        self.order = Order.objects.create(
            customer=self.customer, address="test", phone="+7900",
            total_price=100, products_price=100, status="completed",
        )

    @override_settings(ONEC_ORDER_COMPLETE_URL="")
    def test_skipped_when_no_url(self):
        from apps.integrations.onec.tasks import notify_onec_order_completed
        result = notify_onec_order_completed.apply(args=[self.order.id]).result
        self.assertEqual(result["status"], "skipped")

    @override_settings(ONEC_ORDER_COMPLETE_URL="http://1c.local/complete")
    def test_order_not_found(self):
        from apps.integrations.onec.tasks import notify_onec_order_completed
        result = notify_onec_order_completed.apply(args=[999999]).result
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "order_not_found")

    @patch("apps.integrations.onec.tasks.requests.post")
    @override_settings(ONEC_ORDER_COMPLETE_URL="http://1c.local/complete")
    def test_successful_complete_notification(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        from apps.integrations.onec.tasks import notify_onec_order_completed
        result = notify_onec_order_completed.apply(args=[self.order.id]).result
        self.assertEqual(result["status"], "sent")

        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        self.assertEqual(payload["order_id"], self.order.id)
        self.assertEqual(payload["status"], "completed")


@override_settings(**_TEST_SETTINGS)
class RollbackStuckAssemblyOrdersTests(TestCase):
    def setUp(self):
        self.customer = CustomUser.objects.create(telegram_id=80020)

    def _create_order(self, status="assembly", minutes_ago=15, **kwargs):
        order = Order.objects.create(
            customer=self.customer, address="test", phone="+7900",
            total_price=100, products_price=100, status=status, **kwargs,
        )
        # Update created_at manually (auto_now_add)
        Order.objects.filter(id=order.id).update(
            created_at=timezone.now() - timedelta(minutes=minutes_ago)
        )
        return order

    def test_rolls_back_stuck_orders(self):
        order = self._create_order(status="assembly", minutes_ago=15)

        from apps.integrations.onec.tasks import rollback_stuck_assembly_orders
        rollback_stuck_assembly_orders.apply()

        order.refresh_from_db()
        self.assertEqual(order.status, "new")

    def test_does_not_rollback_recent_orders(self):
        order = self._create_order(status="assembly", minutes_ago=5)

        from apps.integrations.onec.tasks import rollback_stuck_assembly_orders
        rollback_stuck_assembly_orders.apply()

        order.refresh_from_db()
        self.assertEqual(order.status, "assembly")

    def test_does_not_rollback_with_assembler(self):
        order = self._create_order(status="assembly", minutes_ago=15, assembled_by=12345)

        from apps.integrations.onec.tasks import rollback_stuck_assembly_orders
        rollback_stuck_assembly_orders.apply()

        order.refresh_from_db()
        self.assertEqual(order.status, "assembly")

    def test_does_not_rollback_with_onec_guid(self):
        order = self._create_order(status="assembly", minutes_ago=15, onec_guid="abc")

        from apps.integrations.onec.tasks import rollback_stuck_assembly_orders
        rollback_stuck_assembly_orders.apply()

        order.refresh_from_db()
        self.assertEqual(order.status, "assembly")

    def test_does_not_rollback_non_assembly_orders(self):
        order = self._create_order(status="new", minutes_ago=15)

        from apps.integrations.onec.tasks import rollback_stuck_assembly_orders
        rollback_stuck_assembly_orders.apply()

        order.refresh_from_db()
        self.assertEqual(order.status, "new")

    def test_no_stuck_orders_is_noop(self):
        from apps.integrations.onec.tasks import rollback_stuck_assembly_orders
        # Should not raise
        rollback_stuck_assembly_orders.apply()
