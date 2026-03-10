from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from apps.main.models import CustomUser

from ..models import CustomerRFMProfile
from ..services import (
    _get_segment_label,
    _score_frequency,
    _score_monetary,
    _score_recency,
    calculate_all_customers_rfm,
    calculate_customer_rfm,
)


class ScoringFunctionsTestCase(TestCase):
    """Тесты scoring-функций."""

    def test_recency_none_returns_1(self):
        self.assertEqual(_score_recency(None), 1)

    def test_recency_0_days_returns_5(self):
        self.assertEqual(_score_recency(0), 5)

    def test_recency_7_days_returns_5(self):
        self.assertEqual(_score_recency(7), 5)

    def test_recency_30_days_returns_4(self):
        self.assertEqual(_score_recency(30), 4)

    def test_recency_90_days_returns_3(self):
        self.assertEqual(_score_recency(90), 3)

    def test_recency_180_days_returns_2(self):
        self.assertEqual(_score_recency(180), 2)

    def test_recency_365_days_returns_1(self):
        self.assertEqual(_score_recency(365), 1)

    def test_frequency_0_returns_1(self):
        self.assertEqual(_score_frequency(0), 1)

    def test_frequency_2_returns_2(self):
        self.assertEqual(_score_frequency(2), 2)

    def test_frequency_5_returns_3(self):
        self.assertEqual(_score_frequency(5), 3)

    def test_frequency_10_returns_4(self):
        self.assertEqual(_score_frequency(10), 4)

    def test_frequency_20_returns_5(self):
        self.assertEqual(_score_frequency(20), 5)

    def test_monetary_0_returns_1(self):
        self.assertEqual(_score_monetary(Decimal("0")), 1)

    def test_monetary_1000_returns_2(self):
        self.assertEqual(_score_monetary(Decimal("1000")), 2)

    def test_monetary_5000_returns_3(self):
        self.assertEqual(_score_monetary(Decimal("5000")), 3)

    def test_monetary_15000_returns_4(self):
        self.assertEqual(_score_monetary(Decimal("15000")), 4)

    def test_monetary_50000_returns_5(self):
        self.assertEqual(_score_monetary(Decimal("50000")), 5)


class SegmentLabelTestCase(TestCase):
    """Тесты назначения segment_label."""

    def test_champions(self):
        self.assertEqual(_get_segment_label("555"), "champions")

    def test_loyal(self):
        self.assertEqual(_get_segment_label("553"), "loyal")

    def test_potential_loyalists(self):
        self.assertEqual(_get_segment_label("551"), "potential_loyalists")

    def test_new_customers(self):
        self.assertEqual(_get_segment_label("511"), "new_customers")

    def test_at_risk(self):
        self.assertEqual(_get_segment_label("355"), "at_risk")

    def test_hibernating(self):
        self.assertEqual(_get_segment_label("155"), "hibernating")

    def test_lost_fallback(self):
        self.assertEqual(_get_segment_label("111"), "lost")

    def test_unknown_code_returns_lost(self):
        self.assertEqual(_get_segment_label("321"), "lost")


class CalculateCustomerRFMTestCase(TestCase):
    """Тесты calculate_customer_rfm."""

    def _create_user(self, telegram_id, **kwargs):
        defaults = {
            "telegram_id": telegram_id,
            "full_name": f"User {telegram_id}",
        }
        defaults.update(kwargs)
        return CustomUser.objects.create(**defaults)

    def test_customer_with_purchases(self):
        now = timezone.now()
        user = self._create_user(
            9001,
            last_purchase_date=now - timedelta(days=5),
            purchase_count=25,
            total_spent=Decimal("60000"),
        )

        profile = calculate_customer_rfm(user.id)

        self.assertEqual(profile.recency_days, 5)
        self.assertEqual(profile.frequency_count, 25)
        self.assertEqual(profile.monetary_value, Decimal("60000"))
        self.assertEqual(profile.r_score, 5)
        self.assertEqual(profile.f_score, 5)
        self.assertEqual(profile.m_score, 5)
        self.assertEqual(profile.rfm_code, "555")
        self.assertEqual(profile.segment_label, "champions")

    def test_customer_without_purchases(self):
        user = self._create_user(9002)

        profile = calculate_customer_rfm(user.id)

        self.assertIsNone(profile.recency_days)
        self.assertEqual(profile.frequency_count, 0)
        self.assertEqual(profile.monetary_value, Decimal("0"))
        self.assertEqual(profile.r_score, 1)
        self.assertEqual(profile.f_score, 1)
        self.assertEqual(profile.m_score, 1)
        self.assertEqual(profile.rfm_code, "111")
        self.assertEqual(profile.segment_label, "lost")

    def test_creates_profile(self):
        user = self._create_user(9003)

        self.assertFalse(CustomerRFMProfile.objects.filter(customer=user).exists())
        calculate_customer_rfm(user.id)
        self.assertTrue(CustomerRFMProfile.objects.filter(customer=user).exists())

    def test_updates_profile_on_rerun(self):
        now = timezone.now()
        user = self._create_user(
            9004,
            last_purchase_date=now - timedelta(days=200),
            purchase_count=1,
            total_spent=Decimal("500"),
        )

        profile1 = calculate_customer_rfm(user.id)
        self.assertEqual(profile1.rfm_code, "111")

        # Обновляем данные клиента
        user.last_purchase_date = now - timedelta(days=3)
        user.purchase_count = 25
        user.total_spent = Decimal("60000")
        user.save()

        profile2 = calculate_customer_rfm(user.id)

        self.assertEqual(profile2.id, profile1.id)  # тот же объект
        self.assertEqual(profile2.rfm_code, "555")
        self.assertEqual(CustomerRFMProfile.objects.filter(customer=user).count(), 1)

    def test_rfm_code_format(self):
        now = timezone.now()
        user = self._create_user(
            9005,
            last_purchase_date=now - timedelta(days=60),
            purchase_count=7,
            total_spent=Decimal("8000"),
        )

        profile = calculate_customer_rfm(user.id)

        self.assertEqual(len(profile.rfm_code), 3)
        self.assertTrue(profile.rfm_code.isdigit())
        self.assertEqual(profile.rfm_code, "333")


class CalculateAllCustomersRFMTestCase(TestCase):
    """Тесты calculate_all_customers_rfm."""

    def _create_user(self, telegram_id, **kwargs):
        defaults = {
            "telegram_id": telegram_id,
            "full_name": f"User {telegram_id}",
        }
        defaults.update(kwargs)
        return CustomUser.objects.create(**defaults)

    def test_processes_multiple_customers(self):
        now = timezone.now()
        self._create_user(
            8001,
            last_purchase_date=now - timedelta(days=2),
            purchase_count=15,
            total_spent=Decimal("20000"),
        )
        self._create_user(8002)
        self._create_user(
            8003,
            last_purchase_date=now - timedelta(days=100),
            purchase_count=3,
            total_spent=Decimal("3000"),
        )

        result = calculate_all_customers_rfm()

        self.assertEqual(result["total_customers"], 3)
        self.assertEqual(result["processed"], 3)
        self.assertEqual(result["created"], 3)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["skipped"], 0)
        self.assertIsNotNone(result["calculated_at"])

    def test_rerun_updates_existing(self):
        self._create_user(8010)
        self._create_user(8011)

        result1 = calculate_all_customers_rfm()
        result2 = calculate_all_customers_rfm()

        self.assertEqual(result1["created"], 2)
        self.assertEqual(result2["created"], 0)
        self.assertEqual(result2["updated"], 2)
        self.assertEqual(CustomerRFMProfile.objects.count(), 2)

    def test_guest_user_excluded(self):
        """Guest-пользователь (telegram_id == GUEST_TELEGRAM_ID) исключается."""
        guest_tid = getattr(settings, "GUEST_TELEGRAM_ID", 0)
        # Guest уже создан миграцией 0008; убедимся, что он существует.
        self.assertTrue(
            CustomUser.objects.filter(telegram_id=guest_tid).exists(),
            "Guest-пользователь должен существовать (миграция 0008).",
        )

        self._create_user(8030)

        result = calculate_all_customers_rfm()

        self.assertEqual(result["total_customers"], 1)
        self.assertEqual(result["created"], 1)
        self.assertFalse(
            CustomerRFMProfile.objects.filter(
                customer__telegram_id=guest_tid,
            ).exists(),
        )

    def test_all_real_customers_get_profiles(self):
        self._create_user(8020)
        self._create_user(8021)

        calculate_all_customers_rfm()

        guest_tid = getattr(settings, "GUEST_TELEGRAM_ID", 0)
        real_count = CustomUser.objects.exclude(telegram_id=guest_tid).count()
        self.assertEqual(CustomerRFMProfile.objects.count(), real_count)
