"""Тесты CustomerRFMHistory — запись переходов между RFM-сегментами."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.main.models import CustomUser
from apps.rfm.models import CustomerRFMHistory, CustomerRFMProfile
from apps.rfm.services import calculate_all_customers_rfm, calculate_customer_rfm


@override_settings(GUEST_TELEGRAM_ID=0)
class RFMHistoryTestCase(TestCase):

    def _create_user(self, telegram_id, **kwargs):
        defaults = {
            "telegram_id": telegram_id,
            "full_name": f"User {telegram_id}",
        }
        defaults.update(kwargs)
        return CustomUser.objects.create(**defaults)

    def test_first_calculation_creates_initial_history(self):
        """Первый расчёт создаёт запись с transition_type='initial'."""
        user = self._create_user(
            70001,
            last_purchase_date=timezone.now() - timedelta(days=5),
            purchase_count=25,
            total_spent=Decimal("60000"),
        )

        calculate_customer_rfm(user.id)

        history = CustomerRFMHistory.objects.filter(customer=user)
        self.assertEqual(history.count(), 1)

        entry = history.first()
        self.assertEqual(entry.transition_type, "initial")
        self.assertEqual(entry.segment_code, "champions")
        self.assertIsNone(entry.previous_segment_code)
        self.assertEqual(entry.r_score, 5)
        self.assertEqual(entry.f_score, 5)
        self.assertEqual(entry.m_score, 5)

    def test_no_change_no_history(self):
        """Повторный расчёт без изменений не создаёт новую запись."""
        user = self._create_user(
            70002,
            last_purchase_date=timezone.now() - timedelta(days=5),
            purchase_count=25,
            total_spent=Decimal("60000"),
        )

        calculate_customer_rfm(user.id)
        self.assertEqual(CustomerRFMHistory.objects.filter(customer=user).count(), 1)

        # Повторный расчёт — данные не менялись
        calculate_customer_rfm(user.id)
        self.assertEqual(CustomerRFMHistory.objects.filter(customer=user).count(), 1)

    def test_segment_change_creates_history(self):
        """Смена сегмента создаёт запись с transition_type='segment_changed'."""
        now = timezone.now()
        user = self._create_user(
            70003,
            last_purchase_date=now - timedelta(days=5),
            purchase_count=25,
            total_spent=Decimal("60000"),
        )

        calculate_customer_rfm(user.id)

        # Меняем данные так, чтобы сегмент стал lost
        user.last_purchase_date = now - timedelta(days=365)
        user.purchase_count = 1
        user.total_spent = Decimal("500")
        user.save()

        calculate_customer_rfm(user.id)

        history = CustomerRFMHistory.objects.filter(customer=user).order_by("calculated_at")
        self.assertEqual(history.count(), 2)

        second = history.last()
        self.assertEqual(second.transition_type, "segment_changed")
        self.assertEqual(second.previous_segment_code, "champions")
        self.assertEqual(second.segment_code, "lost")

    def test_score_change_creates_history(self):
        """Изменение score без смены сегмента создаёт 'score_changed'."""
        now = timezone.now()
        # Пользователь с rfm_code=111 → lost
        user = self._create_user(
            70004,
            last_purchase_date=now - timedelta(days=365),
            purchase_count=1,
            total_spent=Decimal("500"),
        )

        calculate_customer_rfm(user.id)
        profile = CustomerRFMProfile.objects.get(customer=user)
        self.assertEqual(profile.segment_label, "lost")

        # Меняем monetary чтобы m_score изменился, но сегмент остался lost
        # rfm 112 → lost (не в карте)
        user.total_spent = Decimal("1500")
        user.save()

        calculate_customer_rfm(user.id)

        history = CustomerRFMHistory.objects.filter(customer=user).order_by("calculated_at")
        self.assertEqual(history.count(), 2)

        second = history.last()
        self.assertEqual(second.transition_type, "score_changed")
        self.assertEqual(second.previous_segment_code, "lost")
        self.assertEqual(second.segment_code, "lost")

    def test_history_ordering(self):
        """Записи отсортированы по calculated_at DESC."""
        now = timezone.now()
        user = self._create_user(
            70005,
            last_purchase_date=now - timedelta(days=5),
            purchase_count=25,
            total_spent=Decimal("60000"),
        )

        calculate_customer_rfm(user.id)

        # Меняем данные
        user.last_purchase_date = now - timedelta(days=365)
        user.purchase_count = 1
        user.total_spent = Decimal("500")
        user.save()

        calculate_customer_rfm(user.id)

        history = list(CustomerRFMHistory.objects.filter(customer=user))
        self.assertEqual(len(history), 2)
        # Первый в списке — более новый (DESC ordering)
        self.assertGreaterEqual(history[0].calculated_at, history[1].calculated_at)

    def test_backfill_creates_initial_entries(self):
        """Backfill: существующие профили без истории получают initial-записи."""
        now = timezone.now()
        user = self._create_user(70006)
        # Создаём профиль напрямую (как будто до внедрения истории)
        profile = CustomerRFMProfile.objects.create(
            customer=user,
            recency_days=5,
            frequency_count=10,
            monetary_value=Decimal("5000"),
            r_score=5,
            f_score=4,
            m_score=3,
            rfm_code="543",
            segment_label="loyal",
            calculated_at=now,
        )

        # Имитируем backfill
        CustomerRFMHistory.objects.create(
            customer=user,
            segment_code=profile.segment_label,
            previous_segment_code=None,
            r_score=profile.r_score,
            f_score=profile.f_score,
            m_score=profile.m_score,
            recency_days=profile.recency_days,
            frequency_orders=profile.frequency_count,
            monetary_total=profile.monetary_value,
            transition_type="initial",
            calculated_at=profile.updated_at,
        )

        entry = CustomerRFMHistory.objects.get(customer=user)
        self.assertEqual(entry.transition_type, "initial")
        self.assertEqual(entry.segment_code, "loyal")
        self.assertIsNone(entry.previous_segment_code)

    def test_batch_calculation_creates_history(self):
        """calculate_all_customers_rfm тоже создаёт историю."""
        now = timezone.now()
        self._create_user(
            70007,
            last_purchase_date=now - timedelta(days=5),
            purchase_count=25,
            total_spent=Decimal("60000"),
        )
        self._create_user(70008)

        calculate_all_customers_rfm()

        self.assertEqual(
            CustomerRFMHistory.objects.filter(transition_type="initial").count(), 2,
        )

    def test_batch_no_change_no_duplicate_history(self):
        """Повторный batch-расчёт без изменений не создаёт дубликатов."""
        self._create_user(70009)

        calculate_all_customers_rfm()
        self.assertEqual(CustomerRFMHistory.objects.count(), 1)

        calculate_all_customers_rfm()
        self.assertEqual(CustomerRFMHistory.objects.count(), 1)
