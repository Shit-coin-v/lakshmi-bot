"""Tests for ЮKassa Celery tasks: capture, cancel, expire, TTL finalization."""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.main.models import CustomUser
from apps.orders.models import Order

# Functions are imported inside tasks via:
#   from apps.integrations.payments.yukassa_client import capture_payment, get_payment, ...
# So we mock them at the source module.
_CLIENT = "apps.integrations.payments.yukassa_client"


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class CapturePaymentTaskTests(TestCase):
    def setUp(self):
        self.customer = CustomUser.objects.create(telegram_id=90001)
        self.order = Order.objects.create(
            customer=self.customer,
            address="Test",
            phone="+79001112233",
            total_price=Decimal("500.00"),
            payment_method="sbp",
            payment_id="pay_123",
            payment_status="authorized",
        )

    @patch(f"{_CLIENT}.capture_payment")
    @patch(f"{_CLIENT}.get_payment")
    def test_capture_success(self, mock_get, mock_capture):
        mock_get.return_value = {"status": "waiting_for_capture", "paid": True}
        mock_capture.return_value = {"payment_id": "pay_123", "status": "succeeded"}

        from apps.integrations.payments.tasks import capture_payment_task
        capture_payment_task(self.order.id)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "captured")
        mock_capture.assert_called_once()

    @patch(f"{_CLIENT}.get_payment")
    def test_capture_already_succeeded(self, mock_get):
        mock_get.return_value = {"status": "succeeded", "paid": True}

        from apps.integrations.payments.tasks import capture_payment_task
        capture_payment_task(self.order.id)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "captured")

    @patch(f"{_CLIENT}.get_payment")
    def test_capture_already_canceled(self, mock_get):
        mock_get.return_value = {"status": "canceled", "paid": False}

        from apps.integrations.payments.tasks import capture_payment_task
        capture_payment_task(self.order.id)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "canceled")

    def test_capture_skip_if_not_authorized(self):
        self.order.payment_status = "captured"
        self.order.save(update_fields=["payment_status"])

        from apps.integrations.payments.tasks import capture_payment_task
        capture_payment_task(self.order.id)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "captured")

    def test_capture_skip_if_no_payment_id(self):
        self.order.payment_id = None
        self.order.save(update_fields=["payment_id"])

        from apps.integrations.payments.tasks import capture_payment_task
        capture_payment_task(self.order.id)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "authorized")

    @patch(f"{_CLIENT}.get_payment")
    def test_capture_logical_error_marks_failed(self, mock_get):
        from apps.integrations.payments.yukassa_client import YukassaLogicalError
        mock_get.side_effect = YukassaLogicalError("HTTP 400")

        from apps.integrations.payments.tasks import capture_payment_task
        capture_payment_task(self.order.id)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "failed")

    def test_capture_nonexistent_order(self):
        from apps.integrations.payments.tasks import capture_payment_task
        capture_payment_task(99999)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class CancelPaymentTaskTests(TestCase):
    def setUp(self):
        self.customer = CustomUser.objects.create(telegram_id=90002)
        self.order = Order.objects.create(
            customer=self.customer,
            address="Test",
            phone="+79001112233",
            total_price=Decimal("300.00"),
            payment_method="sbp",
            payment_id="pay_456",
            payment_status="authorized",
        )

    @patch(f"{_CLIENT}.cancel_payment")
    @patch(f"{_CLIENT}.get_payment")
    def test_cancel_authorized_hold(self, mock_get, mock_cancel):
        mock_get.return_value = {"status": "waiting_for_capture"}
        mock_cancel.return_value = {"payment_id": "pay_456", "status": "canceled"}

        from apps.integrations.payments.tasks import cancel_payment_task
        cancel_payment_task(self.order.id)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "canceled")
        mock_cancel.assert_called_once()

    @patch(f"{_CLIENT}.create_refund")
    @patch(f"{_CLIENT}.get_payment")
    def test_cancel_captured_triggers_refund(self, mock_get, mock_refund):
        self.order.payment_status = "captured"
        self.order.save(update_fields=["payment_status"])

        mock_get.return_value = {"status": "succeeded"}
        mock_refund.return_value = {"refund_id": "ref_1", "status": "succeeded"}

        from apps.integrations.payments.tasks import cancel_payment_task
        cancel_payment_task(self.order.id)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "canceled")
        mock_refund.assert_called_once()

    @patch(f"{_CLIENT}.get_payment")
    def test_cancel_already_canceled_remote(self, mock_get):
        mock_get.return_value = {"status": "canceled"}

        from apps.integrations.payments.tasks import cancel_payment_task
        cancel_payment_task(self.order.id)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "canceled")

    def test_cancel_skip_if_no_payment_id(self):
        self.order.payment_id = None
        self.order.save(update_fields=["payment_id"])

        from apps.integrations.payments.tasks import cancel_payment_task
        cancel_payment_task(self.order.id)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "authorized")

    def test_cancel_skip_if_already_canceled(self):
        self.order.payment_status = "canceled"
        self.order.save(update_fields=["payment_status"])

        from apps.integrations.payments.tasks import cancel_payment_task
        cancel_payment_task(self.order.id)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "canceled")


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class FinalizeTtlExpiredTests(TestCase):
    def setUp(self):
        self.customer = CustomUser.objects.create(telegram_id=90003)
        self.order = Order.objects.create(
            customer=self.customer,
            address="Test",
            phone="+79001112233",
            total_price=Decimal("200.00"),
            payment_method="sbp",
            payment_id="pay_ttl",
            payment_status="authorized",
        )

    @patch(f"{_CLIENT}.get_payment")
    def test_ttl_remote_succeeded(self, mock_get):
        mock_get.return_value = {"status": "succeeded"}

        from apps.integrations.payments.tasks import _finalize_ttl_expired
        _finalize_ttl_expired(self.order.id, Order)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "captured")
        self.assertFalse(self.order.manual_check_required)

    @patch(f"{_CLIENT}.get_payment")
    def test_ttl_remote_canceled(self, mock_get):
        mock_get.return_value = {"status": "canceled"}

        from apps.integrations.payments.tasks import _finalize_ttl_expired
        _finalize_ttl_expired(self.order.id, Order)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "canceled")
        self.assertFalse(self.order.manual_check_required)

    @patch(f"{_CLIENT}.get_payment")
    def test_ttl_remote_unknown_status(self, mock_get):
        mock_get.return_value = {"status": "pending"}

        from apps.integrations.payments.tasks import _finalize_ttl_expired
        _finalize_ttl_expired(self.order.id, Order)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "authorized")
        self.assertTrue(self.order.manual_check_required)

    @patch(f"{_CLIENT}.get_payment")
    def test_ttl_remote_unreachable(self, mock_get):
        mock_get.side_effect = Exception("network error")

        from apps.integrations.payments.tasks import _finalize_ttl_expired
        _finalize_ttl_expired(self.order.id, Order)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "authorized")
        self.assertTrue(self.order.manual_check_required)

    def test_ttl_skip_if_not_authorized(self):
        self.order.payment_status = "captured"
        self.order.save(update_fields=["payment_status"])

        from apps.integrations.payments.tasks import _finalize_ttl_expired
        _finalize_ttl_expired(self.order.id, Order)

        self.order.refresh_from_db()
        self.assertFalse(self.order.manual_check_required)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    YUKASSA_PAYMENT_TIMEOUT_MINUTES=15,
)
class ExpirePendingPaymentsTests(TestCase):
    def setUp(self):
        self.customer = CustomUser.objects.create(telegram_id=90004)

    def test_expire_old_pending_orders(self):
        order = Order.objects.create(
            customer=self.customer,
            address="Test",
            phone="+79001112233",
            payment_method="sbp",
            payment_status="pending",
        )
        Order.objects.filter(id=order.id).update(
            created_at=timezone.now() - timedelta(minutes=20)
        )

        from apps.integrations.payments.tasks import expire_pending_payments
        expire_pending_payments()

        order.refresh_from_db()
        self.assertEqual(order.payment_status, "failed")
        self.assertEqual(order.status, "canceled")

    def test_do_not_expire_recent_orders(self):
        order = Order.objects.create(
            customer=self.customer,
            address="Test",
            phone="+79001112233",
            payment_method="sbp",
            payment_status="pending",
        )

        from apps.integrations.payments.tasks import expire_pending_payments
        expire_pending_payments()

        order.refresh_from_db()
        self.assertEqual(order.payment_status, "pending")
        self.assertEqual(order.status, "new")

    def test_do_not_expire_non_sbp(self):
        order = Order.objects.create(
            customer=self.customer,
            address="Test",
            phone="+79001112233",
            payment_method="cash",
            payment_status="none",
        )
        Order.objects.filter(id=order.id).update(
            created_at=timezone.now() - timedelta(minutes=20)
        )

        from apps.integrations.payments.tasks import expire_pending_payments
        expire_pending_payments()

        order.refresh_from_db()
        self.assertEqual(order.status, "new")
