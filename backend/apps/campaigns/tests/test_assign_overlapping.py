"""Тесты защиты assign_campaign_to_customers от пересекающихся кампаний."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.main.models import CustomUser

from ..models import Campaign, CampaignRule, CustomerCampaignAssignment, CustomerSegment
from ..services import assign_campaign_to_customers


class AssignOverlappingTests(TestCase):

    def setUp(self):
        self.now = timezone.now()
        self.user = CustomUser.objects.create(
            telegram_id=500001, promo_enabled=True,
        )

    def _create_segment_with_user(self, slug):
        seg = CustomerSegment.objects.create(
            name=f"Seg {slug}", slug=slug,
            segment_type="manual",
            rules={"card_ids": [self.user.card_id]},
        )
        return seg

    def _create_campaign(self, slug, start_at, end_at, segment=None, **kwargs):
        seg = segment or self._create_segment_with_user(slug)
        defaults = {
            "name": f"Camp {slug}",
            "slug": slug,
            "segment": seg,
            "push_title": "t",
            "push_body": "b",
            "start_at": start_at,
            "end_at": end_at,
            "is_active": True,
        }
        defaults.update(kwargs)
        camp = Campaign.objects.create(**defaults)
        CampaignRule.objects.create(
            campaign=camp, reward_type="fixed_bonus",
            reward_value=Decimal("100"),
        )
        return camp

    def test_active_campaign_blocks_new_assignment(self):
        """Клиент с активной кампанией не попадает в новую."""
        camp1 = self._create_campaign(
            "c1",
            start_at=self.now - timedelta(days=5),
            end_at=self.now + timedelta(days=25),
        )
        CustomerCampaignAssignment.objects.create(
            customer=self.user, campaign=camp1,
        )

        seg2 = self._create_segment_with_user("seg-c2")
        camp2 = self._create_campaign(
            "c2",
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=30),
            segment=seg2,
        )

        result = assign_campaign_to_customers(camp2.id)
        self.assertEqual(result["created_assignments"], 0)
        self.assertEqual(result["skipped_overlapping"], 1)

    def test_future_overlapping_blocks(self):
        """Будущая кампания с пересекающимся периодом блокирует назначение."""
        camp1 = self._create_campaign(
            "c-future",
            start_at=self.now + timedelta(days=10),
            end_at=self.now + timedelta(days=40),
        )
        CustomerCampaignAssignment.objects.create(
            customer=self.user, campaign=camp1,
        )

        seg2 = self._create_segment_with_user("seg-c-future2")
        camp2 = self._create_campaign(
            "c-future2",
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=15),
            segment=seg2,
        )

        result = assign_campaign_to_customers(camp2.id)
        self.assertEqual(result["created_assignments"], 0)
        self.assertEqual(result["skipped_overlapping"], 1)

    def test_future_non_overlapping_allowed(self):
        """Будущая кампания без пересечения дат НЕ блокирует."""
        camp1 = self._create_campaign(
            "c-past",
            start_at=self.now - timedelta(days=30),
            end_at=self.now - timedelta(days=1),
        )
        CustomerCampaignAssignment.objects.create(
            customer=self.user, campaign=camp1,
        )

        seg2 = self._create_segment_with_user("seg-c-new")
        camp2 = self._create_campaign(
            "c-new",
            start_at=self.now - timedelta(hours=1),
            end_at=self.now + timedelta(days=30),
            segment=seg2,
        )

        result = assign_campaign_to_customers(camp2.id)
        self.assertEqual(result["created_assignments"], 1)

    def test_used_one_time_does_not_block(self):
        """Использованная одноразовая кампания не блокирует."""
        camp1 = self._create_campaign(
            "c-used",
            start_at=self.now - timedelta(days=5),
            end_at=self.now + timedelta(days=25),
            one_time_use=True,
        )
        CustomerCampaignAssignment.objects.create(
            customer=self.user, campaign=camp1,
            used=True, used_at=self.now,
        )

        seg2 = self._create_segment_with_user("seg-c-after-used")
        camp2 = self._create_campaign(
            "c-after-used",
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=30),
            segment=seg2,
        )

        result = assign_campaign_to_customers(camp2.id)
        self.assertEqual(result["created_assignments"], 1)

    def test_inactive_campaign_does_not_block(self):
        """Деактивированная кампания не блокирует."""
        camp1 = self._create_campaign(
            "c-inactive",
            start_at=self.now - timedelta(days=5),
            end_at=self.now + timedelta(days=25),
            is_active=False,
        )
        CustomerCampaignAssignment.objects.create(
            customer=self.user, campaign=camp1,
        )

        seg2 = self._create_segment_with_user("seg-c-new2")
        camp2 = self._create_campaign(
            "c-new2",
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=30),
            segment=seg2,
        )

        result = assign_campaign_to_customers(camp2.id)
        self.assertEqual(result["created_assignments"], 1)

    def test_boundary_overlap_blocks(self):
        """end_at одной кампании = start_at другой — пересечение (границы включительны)."""
        boundary = self.now - timedelta(hours=1)
        camp1 = self._create_campaign(
            "c-boundary1",
            start_at=self.now - timedelta(days=30),
            end_at=boundary,
        )
        CustomerCampaignAssignment.objects.create(
            customer=self.user, campaign=camp1,
        )

        seg2 = self._create_segment_with_user("seg-c-boundary2")
        camp2 = self._create_campaign(
            "c-boundary2",
            start_at=boundary,  # start_at == end_at camp1
            end_at=boundary + timedelta(days=30),
            segment=seg2,
        )

        result = assign_campaign_to_customers(camp2.id)
        self.assertEqual(result["created_assignments"], 0)
        self.assertEqual(result["skipped_overlapping"], 1)

    def test_no_assignment_allows_new(self):
        """Клиент без assignment назначается нормально."""
        seg = self._create_segment_with_user("seg-clean")
        camp = self._create_campaign(
            "c-clean",
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=30),
            segment=seg,
        )

        result = assign_campaign_to_customers(camp.id)
        self.assertEqual(result["created_assignments"], 1)
