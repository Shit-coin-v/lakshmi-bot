"""Тесты monthly bonus tier фиксации, Celery-задач и backfill."""

import calendar
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.main.models import CustomUser
from apps.rfm.models import CustomerBonusTier, CustomerRFMProfile
from apps.rfm.services import compute_segment_for_customer_data
from apps.rfm.tasks import fix_monthly_bonus_tiers, recalculate_all_rfm


class ComputeSegmentTests(TestCase):
    """Тесты общей утилиты compute_segment_for_customer_data."""

    def test_champions_segment(self):
        now = timezone.now()
        rfm_code, label = compute_segment_for_customer_data(
            last_purchase_date=now - timedelta(days=3),
            purchase_count=25,
            total_spent=Decimal("60000"),
            now=now,
        )
        self.assertEqual(label, "champions")

    def test_lost_segment_no_data(self):
        _, label = compute_segment_for_customer_data(
            last_purchase_date=None,
            purchase_count=None,
            total_spent=None,
        )
        self.assertEqual(label, "lost")

    def test_standard_segment(self):
        now = timezone.now()
        _, label = compute_segment_for_customer_data(
            last_purchase_date=now - timedelta(days=200),
            purchase_count=1,
            total_spent=Decimal("500"),
            now=now,
        )
        self.assertNotEqual(label, "champions")


@override_settings(GUEST_TELEGRAM_ID=0)
class FixMonthlyBonusTiersTests(TestCase):

    def setUp(self):
        self.user_champion = CustomUser.objects.create(
            telegram_id=100001,
            last_purchase_date=timezone.now() - timedelta(days=2),
            purchase_count=30,
            total_spent=Decimal("70000"),
        )
        self.user_standard = CustomUser.objects.create(
            telegram_id=100002,
            last_purchase_date=timezone.now() - timedelta(days=200),
            purchase_count=1,
            total_spent=Decimal("500"),
        )
        self.user_no_data = CustomUser.objects.create(
            telegram_id=100003,
        )

    def test_creates_tiers_for_all_customers(self):
        result = fix_monthly_bonus_tiers()
        total_created = result["champions"] + result["standard"]
        self.assertEqual(total_created, 3)

    def test_champion_gets_champions_tier(self):
        fix_monthly_bonus_tiers()
        tier = CustomerBonusTier.objects.get(customer=self.user_champion)
        self.assertEqual(tier.tier, "champions")

    def test_standard_gets_standard_tier(self):
        fix_monthly_bonus_tiers()
        tier = CustomerBonusTier.objects.get(customer=self.user_standard)
        self.assertEqual(tier.tier, "standard")

    def test_no_data_gets_standard_tier(self):
        fix_monthly_bonus_tiers()
        tier = CustomerBonusTier.objects.get(customer=self.user_no_data)
        self.assertEqual(tier.tier, "standard")

    def test_effective_dates_cover_current_month(self):
        fix_monthly_bonus_tiers()
        tier = CustomerBonusTier.objects.get(customer=self.user_champion)
        today = timezone.localdate()
        self.assertEqual(tier.effective_from, today.replace(day=1))
        last_day = calendar.monthrange(today.year, today.month)[1]
        self.assertEqual(tier.effective_to, today.replace(day=last_day))

    def test_does_not_overwrite_existing(self):
        fix_monthly_bonus_tiers()
        tier = CustomerBonusTier.objects.get(customer=self.user_champion)
        original_created = tier.created_at

        result = fix_monthly_bonus_tiers()
        self.assertEqual(result["skipped_existing"], 3)

        tier.refresh_from_db()
        self.assertEqual(tier.created_at, original_created)

    def test_does_not_use_rfm_profile(self):
        """Monthly batch вычисляет eligibility самостоятельно, не читает CustomerRFMProfile."""
        # Создаём устаревший RFM-профиль, говорящий что клиент lost
        CustomerRFMProfile.objects.create(
            customer=self.user_champion,
            segment_label="lost",
            rfm_code="111",
            calculated_at=timezone.now() - timedelta(days=2),
        )
        fix_monthly_bonus_tiers()
        tier = CustomerBonusTier.objects.get(customer=self.user_champion)
        # Должен быть champions по агрегатам CustomUser, а не lost по RFM
        self.assertEqual(tier.tier, "champions")

    def test_stores_segment_label_at_fixation(self):
        fix_monthly_bonus_tiers()
        tier = CustomerBonusTier.objects.get(customer=self.user_champion)
        self.assertEqual(tier.segment_label_at_fixation, "champions")


@override_settings(GUEST_TELEGRAM_ID=0)
class RecalculateRFMTests(TestCase):

    def setUp(self):
        self.user = CustomUser.objects.create(
            telegram_id=200001,
            last_purchase_date=timezone.now() - timedelta(days=2),
            purchase_count=25,
            total_spent=Decimal("60000"),
        )

    def test_creates_rfm_profile(self):
        result = recalculate_all_rfm()
        self.assertEqual(result["created"], 1)
        profile = CustomerRFMProfile.objects.get(customer=self.user)
        self.assertEqual(profile.segment_label, "champions")

    def test_does_not_touch_bonus_tier(self):
        today = timezone.localdate()
        CustomerBonusTier.objects.create(
            customer=self.user,
            tier="standard",
            segment_label_at_fixation="lost",
            effective_from=today.replace(day=1),
            effective_to=today.replace(day=28),
        )
        recalculate_all_rfm()
        tier = CustomerBonusTier.objects.get(customer=self.user)
        self.assertEqual(tier.tier, "standard")  # не изменился

    def test_does_not_touch_assignments(self):
        from apps.campaigns.models import Campaign, CustomerCampaignAssignment, CustomerSegment

        seg = CustomerSegment.objects.create(name="Test", slug="test-seg")
        camp = Campaign.objects.create(
            name="C", slug="c-slug", segment=seg,
            push_title="t", push_body="b",
            start_at=timezone.now() - timedelta(days=1),
            end_at=timezone.now() + timedelta(days=30),
        )
        assignment = CustomerCampaignAssignment.objects.create(
            customer=self.user, campaign=camp,
        )
        recalculate_all_rfm()
        assignment.refresh_from_db()
        self.assertFalse(assignment.used)


@override_settings(GUEST_TELEGRAM_ID=0)
class BackfillBonusTiersCommandTests(TestCase):
    """Тесты management command backfill_bonus_tiers."""

    def setUp(self):
        self.user_champion = CustomUser.objects.create(
            telegram_id=600001,
            last_purchase_date=timezone.now() - timedelta(days=2),
            purchase_count=30,
            total_spent=Decimal("70000"),
        )
        self.user_standard = CustomUser.objects.create(
            telegram_id=600002,
            last_purchase_date=timezone.now() - timedelta(days=200),
            purchase_count=1,
            total_spent=Decimal("500"),
        )

    def test_creates_tiers_for_current_month(self):
        out = StringIO()
        call_command("backfill_bonus_tiers", stdout=out)
        self.assertEqual(CustomerBonusTier.objects.count(), 2)

        tier = CustomerBonusTier.objects.get(customer=self.user_champion)
        self.assertEqual(tier.tier, "champions")

        today = timezone.localdate()
        self.assertEqual(tier.effective_from, today.replace(day=1))
        last_day = calendar.monthrange(today.year, today.month)[1]
        self.assertEqual(tier.effective_to, today.replace(day=last_day))

    def test_idempotent_on_rerun(self):
        call_command("backfill_bonus_tiers", stdout=StringIO())
        call_command("backfill_bonus_tiers", stdout=StringIO())
        self.assertEqual(CustomerBonusTier.objects.count(), 2)

    def test_uses_same_eligibility_as_monthly_batch(self):
        """Backfill использует compute_segment_for_customer_data — ту же логику, что и monthly batch."""
        call_command("backfill_bonus_tiers", stdout=StringIO())
        tier = CustomerBonusTier.objects.get(customer=self.user_champion)
        self.assertEqual(tier.segment_label_at_fixation, "champions")
