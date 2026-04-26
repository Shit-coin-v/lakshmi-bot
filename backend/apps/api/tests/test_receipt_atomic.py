"""Тесты атомарности обработки чека (H9 из audit-report.md).

Цикл создания Transaction'ов в onec_receipt обёрнут в db_tx.atomic().
Гарантия: либо все строки чека созданы, либо ни одна.
"""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.db import IntegrityError

from apps.common import security
from apps.loyalty.models import CustomUser, Transaction

from .base import OneCTestBase


class ReceiptAtomicTests(OneCTestBase):
    """Atomic-обёртка над циклом строк чека (H9)."""

    def setUp(self):
        super().setUp()
        CustomUser.objects.update_or_create(
            telegram_id=settings.GUEST_TELEGRAM_ID,
            defaults={"full_name": "Гость"},
        )

    def _post_receipt(self, payload: dict, *, idem: str):
        body = json.dumps(payload).encode()
        return self.client.post(
            "/onec/receipt",
            data=body,
            content_type="application/json",
            follow=True,
            HTTP_X_API_KEY=security.API_KEY,
            HTTP_X_IDEMPOTENCY_KEY=idem,
        )

    def _two_line_payload(self, *, card_id: str, receipt_guid: str = "R-ATOMIC") -> dict:
        return {
            "receipt_guid": receipt_guid,
            "datetime": "2026-04-26T12:00:00+00:00",
            "store_id": "77",
            "customer": {"card_id": card_id},
            "positions": [
                {
                    "product_code": "SKU-A1",
                    "quantity": "1",
                    "price": "100.00",
                    "line_number": 1,
                    "bonus_earned": "1.00",
                },
                {
                    "product_code": "SKU-A2",
                    "quantity": "2",
                    "price": "50.00",
                    "line_number": 2,
                    "bonus_earned": "1.00",
                },
            ],
            "totals": {
                "total_amount": "200.00",
                "discount_total": "0.00",
                "bonus_spent": "0.00",
                "bonus_earned": "2.00",
            },
        }

    def test_smoke_two_lines_both_created(self):
        """Smoke: оба Transaction создаются в одной atomic-транзакции."""
        user = CustomUser.objects.create(telegram_id=9501, bonuses=Decimal("0"))
        payload = self._two_line_payload(card_id=user.card_id)

        response = self._post_receipt(
            payload, idem="00000000-0000-0000-0000-000000009501",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["created_count"], 2)

        # Обе строки чека в БД.
        guids = list(
            Transaction.objects.filter(receipt_guid="R-ATOMIC")
            .order_by("receipt_line")
            .values_list("receipt_line", flat=True)
        )
        self.assertEqual(guids, [1, 2])

        # Бонусы начислены целиком (2 + 0).
        user.refresh_from_db()
        self.assertEqual(user.bonuses, Decimal("2.00"))

    def test_rollback_on_failure_in_second_line(self):
        """Если вторая строка падает с IntegrityError, первая откатывается.

        Atomic-обёртка должна гарантировать: либо обе Transaction'ы
        созданы, либо ни одна. Эмулируем сбой через monkey-patch
        Transaction.objects.get_or_create — на втором вызове бросаем
        IntegrityError.
        """
        user = CustomUser.objects.create(telegram_id=9502, bonuses=Decimal("0"))
        payload = self._two_line_payload(
            card_id=user.card_id, receipt_guid="R-ROLLBACK",
        )

        original_get_or_create = Transaction.objects.get_or_create
        call_state = {"calls": 0}

        def flaky_get_or_create(*args, **kwargs):
            call_state["calls"] += 1
            if call_state["calls"] == 2:
                # Эмулируем гонку с уникальным constraint на второй строке.
                raise IntegrityError("simulated unique violation on line 2")
            return original_get_or_create(*args, **kwargs)

        with patch.object(
            Transaction.objects, "get_or_create", side_effect=flaky_get_or_create,
        ):
            response = self._post_receipt(
                payload, idem="00000000-0000-0000-0000-000000009502",
            )

        # Вьюха ловит IntegrityError на line 2 → DuplicateReceiptLineError → 400.
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "duplicate_receipt_line")

        # Главное: благодаря atomic первая строка тоже откатилась.
        # В БД не должно быть ни одной Transaction по этому receipt_guid.
        self.assertEqual(
            Transaction.objects.filter(receipt_guid="R-ROLLBACK").count(),
            0,
            "atomic должен был откатить первую строку при сбое на второй",
        )

        # Бонусы пользователя не изменились (ничего не зафиксировалось).
        user.refresh_from_db()
        self.assertEqual(user.bonuses, Decimal("0.00"))
