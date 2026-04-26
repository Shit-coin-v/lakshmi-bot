"""Тесты retry-механики webhook при гонке Order.DoesNotExist (C3)."""

import json
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase

from apps.main.models import CustomUser
from apps.orders.models import Order

_WEBHOOK = "apps.integrations.payments.webhook"
_TASKS = "apps.integrations.payments.tasks"
_NOTIF = "apps.notifications.tasks"
_ONEC = "apps.integrations.onec.tasks"
_WEBHOOK_URL = "/api/payments/webhook/"


class WebhookOrderRaceTests(TestCase):
    """Webhook пришёл раньше, чем Order закоммичен в БД."""

    def setUp(self):
        self.client = Client()
        self._ip_patcher = patch(f"{_WEBHOOK}._is_yukassa_ip", return_value=True)
        self._ip_patcher.start()

    def tearDown(self):
        self._ip_patcher.stop()

    def _post_webhook(self, event, payment_id):
        payload = {"event": event, "object": {"id": payment_id}}
        return self.client.post(
            _WEBHOOK_URL,
            data=json.dumps(payload),
            content_type="application/json",
        )

    @patch(f"{_TASKS}.retry_webhook_handler.apply_async")
    def test_authorized_unknown_order_schedules_retry(self, mock_retry):
        response = self._post_webhook("payment.waiting_for_capture", "pay_unknown_1")
        self.assertEqual(response.status_code, 200)
        mock_retry.assert_called_once_with(
            args=["payment.waiting_for_capture", "pay_unknown_1"], countdown=10,
        )

    @patch(f"{_TASKS}.retry_webhook_handler.apply_async")
    def test_canceled_unknown_order_schedules_retry(self, mock_retry):
        response = self._post_webhook("payment.canceled", "pay_unknown_2")
        self.assertEqual(response.status_code, 200)
        mock_retry.assert_called_once_with(
            args=["payment.canceled", "pay_unknown_2"], countdown=10,
        )


class RetryWebhookHandlerTests(TestCase):
    """Прямые тесты Celery-таски retry_webhook_handler."""

    @patch(f"{_NOTIF}.send_order_push_task.delay")
    @patch(f"{_NOTIF}.notify_pickers_new_order.delay")
    @patch(f"{_ONEC}.send_order_to_onec.delay")
    def test_processes_when_order_appeared(self, mock_onec, mock_pickers, mock_push):
        from apps.integrations.payments.tasks import retry_webhook_handler

        customer = CustomUser.objects.create(telegram_id=90020)
        order = Order.objects.create(
            customer=customer,
            address="Test",
            phone="+79001112233",
            total_price=Decimal("500.00"),
            payment_method="sbp",
            payment_id="pay_late_1",
            payment_status="pending",
        )

        with self.captureOnCommitCallbacks(execute=True):
            retry_webhook_handler(
                "payment.waiting_for_capture", "pay_late_1",
            )

        order.refresh_from_db()
        self.assertEqual(order.payment_status, "authorized")
        mock_onec.assert_called_once_with(order.id)
        mock_pickers.assert_called_once_with(order.id)

    def test_logs_after_max_retries_when_order_never_appears(self):
        # Прямой вызов с превышенным retries — задача должна тихо завершиться
        # с ERROR-логом, не падая.
        from apps.integrations.payments.tasks import retry_webhook_handler

        # Обходим self.retry, симулируя последний возможный retry.
        with patch.object(
            retry_webhook_handler, "retry",
            side_effect=AssertionError("retry should not be called"),
        ):
            with self.assertLogs(
                "apps.integrations.payments.tasks", level="ERROR",
            ) as cm:
                # Задача нативно использует self.request.retries; для последнего
                # retry возвращаем длину массива backoff'ов.
                from apps.integrations.payments.tasks import _WEBHOOK_RETRY_BACKOFFS
                with patch(
                    "celery.app.task.Context.retries",
                    new_callable=lambda: len(_WEBHOOK_RETRY_BACKOFFS),
                ):
                    retry_webhook_handler.run(
                        "payment.waiting_for_capture", "pay_never_appears",
                    )

            self.assertTrue(any("still not found" in m for m in cm.output))
