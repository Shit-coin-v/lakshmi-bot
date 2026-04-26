"""Тесты разделения веток except в _finalize_ttl_expired.

Проверяем H5 (split except Exception): YukassaLogicalError,
сетевая ошибка (RequestException) и неожиданное исключение
обрабатываются разными ветками с разными уровнями логирования.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from requests.exceptions import ConnectionError as RequestsConnectionError

from apps.integrations.payments.yukassa_client import YukassaLogicalError
from apps.main.models import CustomUser
from apps.orders.models import Order

# Точка мокирования совпадает с импортом внутри tasks.py:
#   from apps.integrations.payments.yukassa_client import get_payment
_CLIENT = "apps.integrations.payments.yukassa_client"


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class FinalizeTtlExpiredSplitExceptTests(TestCase):
    """_finalize_ttl_expired должен разделять логические/сетевые/прочие ошибки."""

    def setUp(self):
        self.customer = CustomUser.objects.create(telegram_id=92001)
        self.order = Order.objects.create(
            customer=self.customer,
            address="Test",
            phone="+79001112233",
            total_price=Decimal("300.00"),
            payment_method="sbp",
            payment_id="pay_split",
            payment_status="authorized",
        )

    @patch(f"{_CLIENT}.get_payment")
    def test_logical_error_logs_error_and_flags(self, mock_get):
        """YukassaLogicalError → log.error + manual_check_required."""
        mock_get.side_effect = YukassaLogicalError("HTTP 400 bad request")

        from apps.integrations.payments.tasks import _finalize_ttl_expired

        with self.assertLogs("apps.integrations.payments.tasks", level="ERROR") as cm:
            _finalize_ttl_expired(self.order.id, Order)

        self.order.refresh_from_db()
        self.assertTrue(self.order.manual_check_required)
        # Сообщение должно явно упоминать logical error.
        joined = "\n".join(cm.output)
        self.assertIn("logical error", joined.lower())

    @patch(f"{_CLIENT}.get_payment")
    def test_network_error_logs_warning_and_flags(self, mock_get):
        """RequestException → log.warning + manual_check_required."""
        mock_get.side_effect = RequestsConnectionError("connection refused")

        from apps.integrations.payments.tasks import _finalize_ttl_expired

        with self.assertLogs("apps.integrations.payments.tasks", level="WARNING") as cm:
            _finalize_ttl_expired(self.order.id, Order)

        self.order.refresh_from_db()
        self.assertTrue(self.order.manual_check_required)
        # Должно быть зафиксировано как network error на уровне WARNING.
        warning_lines = [r for r in cm.records if r.levelname == "WARNING"]
        self.assertTrue(warning_lines, "ожидался хотя бы один WARNING")
        joined = "\n".join(r.getMessage() for r in warning_lines)
        self.assertIn("network error", joined.lower())

    @patch(f"{_CLIENT}.get_payment")
    def test_unexpected_error_logs_exception_and_flags(self, mock_get):
        """Неожиданная Exception → log.exception (с traceback) + manual_check_required."""

        class _OddError(Exception):
            pass

        mock_get.side_effect = _OddError("totally unexpected")

        from apps.integrations.payments.tasks import _finalize_ttl_expired

        with self.assertLogs("apps.integrations.payments.tasks", level="ERROR") as cm:
            _finalize_ttl_expired(self.order.id, Order)

        self.order.refresh_from_db()
        self.assertTrue(self.order.manual_check_required)
        # logger.exception → ERROR-уровень с traceback (exc_info).
        error_records = [r for r in cm.records if r.levelname == "ERROR"]
        self.assertTrue(error_records, "ожидался хотя бы один ERROR")
        # Хотя бы одна запись должна содержать exc_info (traceback).
        self.assertTrue(
            any(r.exc_info is not None for r in error_records),
            "logger.exception обязан включать traceback (exc_info)",
        )
        joined = "\n".join(r.getMessage() for r in error_records)
        self.assertIn("unexpected", joined.lower())
