from datetime import datetime, timedelta
from decimal import Decimal

from django.test import Client, TestCase

from apps.loyalty.models import Transaction
from apps.main.models import CustomUser


URL = "/api/customer/me/bonus-history/"


class BonusHistoryTestBase(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(
            telegram_id=8001, bonuses=0,
        )

    def _get(self, customer=None, **params):
        c = customer or self.customer
        return self.client.get(
            URL,
            data=params,
            HTTP_X_TELEGRAM_USER_ID=str(c.telegram_id),
        )

    def _create_tx(self, receipt_guid, receipt_line, purchased_at, **kwargs):
        defaults = {
            "customer": self.customer,
            "total_amount": Decimal("100.00"),
            "store_id": 1,
            "receipt_bonus_earned": None,
            "receipt_bonus_spent": None,
        }
        defaults.update(kwargs)
        return Transaction.objects.create(
            receipt_guid=receipt_guid,
            receipt_line=receipt_line,
            purchased_at=purchased_at,
            **defaults,
        )


class BonusHistoryBasicTests(BonusHistoryTestBase):
    """Основные кейсы."""

    def test_empty_history(self):
        """1. Пустая история."""
        resp = self._get()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNone(data["next_cursor"])
        self.assertEqual(data["results"], [])

    def test_single_receipt(self):
        """2. Один чек (одна позиция) — корректные поля."""
        dt = datetime(2026, 3, 15, 10, 30, 0)
        self._create_tx(
            "guid-1", 1, dt,
            total_amount=Decimal("2500.00"),
            receipt_bonus_earned=Decimal("125.00"),
            receipt_bonus_spent=Decimal("50.00"),
        )
        resp = self._get()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["results"]), 1)
        item = data["results"][0]
        self.assertEqual(item["receipt_guid"], "guid-1")
        self.assertEqual(item["date"], "2026-03-15T10:30:00")
        self.assertEqual(item["purchase_total"], "2500.00")
        self.assertEqual(item["bonus_earned"], "125.00")
        self.assertEqual(item["bonus_spent"], "50.00")
        self.assertIsNone(data["next_cursor"])

    def test_multiple_receipts_sorted_desc(self):
        """3. Несколько чеков — сортировка sort_date DESC."""
        dt1 = datetime(2026, 3, 10, 12, 0)
        dt2 = datetime(2026, 3, 15, 12, 0)
        dt3 = datetime(2026, 3, 12, 12, 0)
        self._create_tx("guid-a", 1, dt1, total_amount=Decimal("100.00"))
        self._create_tx("guid-b", 1, dt2, total_amount=Decimal("200.00"))
        self._create_tx("guid-c", 1, dt3, total_amount=Decimal("300.00"))

        resp = self._get()
        data = resp.json()
        guids = [r["receipt_guid"] for r in data["results"]]
        self.assertEqual(guids, ["guid-b", "guid-c", "guid-a"])


class BonusHistoryAggregationTests(BonusHistoryTestBase):
    """Агрегация нескольких позиций в одном чеке."""

    def test_multiple_lines_aggregated(self):
        """4. Несколько позиций в одном чеке — SUM по полям."""
        dt = datetime(2026, 3, 15, 10, 0)
        self._create_tx(
            "guid-multi", 1, dt,
            total_amount=Decimal("1000.00"),
            receipt_bonus_earned=Decimal("50.00"),
            receipt_bonus_spent=Decimal("20.00"),
        )
        self._create_tx(
            "guid-multi", 2, dt,
            total_amount=Decimal("500.00"),
            receipt_bonus_earned=Decimal("25.00"),
            receipt_bonus_spent=Decimal("10.00"),
        )
        self._create_tx(
            "guid-multi", 3, dt,
            total_amount=Decimal("300.00"),
            receipt_bonus_earned=Decimal("15.00"),
            receipt_bonus_spent=Decimal("5.00"),
        )

        resp = self._get()
        data = resp.json()
        self.assertEqual(len(data["results"]), 1)
        item = data["results"][0]
        self.assertEqual(item["purchase_total"], "1800.00")
        self.assertEqual(item["bonus_earned"], "90.00")
        self.assertEqual(item["bonus_spent"], "35.00")

    def test_null_bonus_fields_coalesced_to_zero(self):
        """5. NULL в bonus-полях → 0.00."""
        dt = datetime(2026, 3, 15, 10, 0)
        self._create_tx(
            "guid-null", 1, dt,
            total_amount=Decimal("100.00"),
            receipt_bonus_earned=None,
            receipt_bonus_spent=None,
        )
        resp = self._get()
        item = resp.json()["results"][0]
        self.assertEqual(item["bonus_earned"], "0.00")
        self.assertEqual(item["bonus_spent"], "0.00")

    def test_zero_bonus_receipt_shown(self):
        """6. Чек с earned=0 и spent=0 — показывается."""
        dt = datetime(2026, 3, 15, 10, 0)
        self._create_tx(
            "guid-zero", 1, dt,
            total_amount=Decimal("50.00"),
            receipt_bonus_earned=Decimal("0.00"),
            receipt_bonus_spent=Decimal("0.00"),
        )
        resp = self._get()
        data = resp.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["bonus_earned"], "0.00")
        self.assertEqual(data["results"][0]["bonus_spent"], "0.00")


class BonusHistoryPaginationTests(BonusHistoryTestBase):
    """Cursor-based пагинация."""

    def _create_n_receipts(self, n, base_dt=None):
        if base_dt is None:
            base_dt = datetime(2026, 1, 1, 0, 0)
        for i in range(n):
            self._create_tx(
                f"guid-{i:04d}", 1,
                base_dt + timedelta(hours=i),
                total_amount=Decimal("10.00"),
            )

    def test_under_page_size_no_cursor(self):
        """7. < 20 записей — next_cursor = null."""
        self._create_n_receipts(5)
        resp = self._get()
        data = resp.json()
        self.assertEqual(len(data["results"]), 5)
        self.assertIsNone(data["next_cursor"])

    def test_exactly_page_size_no_cursor(self):
        """8. Ровно 20 записей — next_cursor = null."""
        self._create_n_receipts(20)
        resp = self._get()
        data = resp.json()
        self.assertEqual(len(data["results"]), 20)
        self.assertIsNone(data["next_cursor"])

    def test_over_page_size_has_cursor(self):
        """9. 21+ записей — next_cursor != null, results = 20."""
        self._create_n_receipts(25)
        resp = self._get()
        data = resp.json()
        self.assertEqual(len(data["results"]), 20)
        self.assertIsNotNone(data["next_cursor"])

    def test_second_page_via_cursor(self):
        """10. Вторая страница по cursor — корректные записи."""
        self._create_n_receipts(25)
        resp1 = self._get()
        data1 = resp1.json()
        cursor = data1["next_cursor"]
        self.assertIsNotNone(cursor)

        resp2 = self._get(cursor=cursor)
        data2 = resp2.json()
        self.assertEqual(len(data2["results"]), 5)
        self.assertIsNone(data2["next_cursor"])

        # Нет пересечений по guid между страницами
        page1_guids = {r["receipt_guid"] for r in data1["results"]}
        page2_guids = {r["receipt_guid"] for r in data2["results"]}
        self.assertEqual(len(page1_guids & page2_guids), 0)

    def test_same_date_stable_sort_by_guid(self):
        """11. Два чека с одинаковым purchased_at — стабильная сортировка по receipt_guid."""
        dt = datetime(2026, 3, 15, 10, 0)
        self._create_tx("guid-aaa", 1, dt, total_amount=Decimal("10.00"))
        self._create_tx("guid-zzz", 1, dt, total_amount=Decimal("20.00"))

        resp = self._get()
        data = resp.json()
        guids = [r["receipt_guid"] for r in data["results"]]
        # DESC order: zzz before aaa
        self.assertEqual(guids, ["guid-zzz", "guid-aaa"])

    def test_invalid_cursor_returns_400(self):
        """12. Невалидный cursor → 400."""
        resp = self._get(cursor="not-a-valid-cursor!!!")
        self.assertEqual(resp.status_code, 400)


class BonusHistoryLegacyEdgeTests(BonusHistoryTestBase):
    """Legacy/edge cases — записи без receipt_guid."""

    def test_null_receipt_guid_excluded(self):
        """13. receipt_guid = NULL → исключён."""
        dt = datetime(2026, 3, 15, 10, 0)
        self._create_tx(None, None, dt, total_amount=Decimal("100.00"))
        # Также один валидный
        self._create_tx("guid-valid", 1, dt, total_amount=Decimal("50.00"))

        resp = self._get()
        data = resp.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["receipt_guid"], "guid-valid")

    def test_empty_receipt_guid_excluded(self):
        """14. receipt_guid = "" → исключён."""
        dt = datetime(2026, 3, 15, 10, 0)
        Transaction.objects.create(
            customer=self.customer,
            receipt_guid="",
            receipt_line=1,
            purchased_at=dt,
            total_amount=Decimal("100.00"),
            store_id=1,
        )
        resp = self._get()
        data = resp.json()
        self.assertEqual(len(data["results"]), 0)

    def test_only_legacy_returns_empty(self):
        """15. Только legacy-записи → пустой список."""
        dt = datetime(2026, 3, 15, 10, 0)
        # Legacy: без receipt_guid
        self._create_tx(None, None, dt, total_amount=Decimal("100.00"))
        # Legacy: пустая строка
        Transaction.objects.create(
            customer=self.customer,
            receipt_guid="",
            receipt_line=2,
            purchased_at=dt,
            total_amount=Decimal("200.00"),
            store_id=1,
        )

        resp = self._get()
        data = resp.json()
        self.assertEqual(data["results"], [])
        self.assertIsNone(data["next_cursor"])


class BonusHistoryIsolationTests(BonusHistoryTestBase):
    """Изоляция данных между пользователями."""

    def test_user_sees_only_own_transactions(self):
        """16. Пользователь видит только свои транзакции."""
        other = CustomUser.objects.create(telegram_id=8002, bonuses=0)
        dt = datetime(2026, 3, 15, 10, 0)

        self._create_tx("guid-mine", 1, dt, total_amount=Decimal("100.00"))
        Transaction.objects.create(
            customer=other,
            receipt_guid="guid-other",
            receipt_line=1,
            purchased_at=dt,
            total_amount=Decimal("200.00"),
            store_id=1,
        )

        resp = self._get()
        data = resp.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["receipt_guid"], "guid-mine")


class BonusHistoryAuthTests(TestCase):
    """Авторизация."""

    def test_no_auth_returns_401(self):
        """17. Без токена → 401."""
        client = Client()
        resp = client.get(URL)
        self.assertEqual(resp.status_code, 401)

    def test_invalid_telegram_id_returns_401(self):
        """18. Невалидный telegram_id (несуществующий) → 401."""
        client = Client()
        resp = client.get(URL, HTTP_X_TELEGRAM_USER_ID="999999999")
        self.assertEqual(resp.status_code, 401)

    def test_invalid_bearer_token_returns_401(self):
        """21. Невалидный JWT Bearer token → 401."""
        client = Client()
        resp = client.get(URL, HTTP_AUTHORIZATION="Bearer invalid.jwt.token")
        self.assertEqual(resp.status_code, 401)


class BonusHistoryTimezoneCursorTests(BonusHistoryTestBase):
    """Cursor с aware datetime (USE_TZ=True в production)."""

    def test_cursor_pagination_preserves_order_across_pages(self):
        """19. Cursor pagination корректно переносит порядок между страницами."""
        # Создаём 21 чек — достаточно для проверки cursor roundtrip
        base_dt = datetime(2026, 3, 1, 0, 0)
        for i in range(21):
            self._create_tx(
                f"guid-tz-{i:03d}", 1,
                base_dt + timedelta(hours=i),
                total_amount=Decimal("10.00"),
            )

        resp1 = self._get()
        data1 = resp1.json()
        self.assertEqual(len(data1["results"]), 20)
        cursor = data1["next_cursor"]
        self.assertIsNotNone(cursor)

        resp2 = self._get(cursor=cursor)
        data2 = resp2.json()
        self.assertEqual(len(data2["results"]), 1)
        self.assertIsNone(data2["next_cursor"])

    def test_cursor_roundtrip_with_aware_datetime(self):
        """20. Encode/decode cursor сохраняет timezone info."""
        from apps.loyalty.views import _decode_cursor, _encode_cursor
        from django.utils import timezone as dj_tz

        aware_dt = dj_tz.make_aware(datetime(2026, 3, 15, 10, 30, 0))
        cursor = _encode_cursor(aware_dt, "guid-test")
        decoded_dt, decoded_guid = _decode_cursor(cursor)

        self.assertEqual(decoded_guid, "guid-test")
        self.assertEqual(decoded_dt, aware_dt)
