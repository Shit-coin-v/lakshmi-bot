from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.main.models import CustomUser

from ..models import Campaign, CustomerCampaignAssignment, CustomerSegment
from ..services import CampaignError, assign_campaign_to_customers


class AssignCampaignTestCase(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.segment = CustomerSegment.objects.create(
            name="Test Segment",
            slug="test-segment",
            segment_type="manual",
            rules={"card_ids": []},
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            slug="test-campaign",
            segment=self.segment,
            push_title="Title",
            push_body="Body",
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=1),
            is_active=True,
        )

    def _create_user(self, telegram_id, **kwargs):
        defaults = {
            "telegram_id": telegram_id,
            "full_name": f"User {telegram_id}",
            "promo_enabled": True,
        }
        defaults.update(kwargs)
        return CustomUser.objects.create(**defaults)

    # --- manual segment ---

    def test_manual_segment_creates_assignments(self):
        u1 = self._create_user(1001)
        u2 = self._create_user(1002)
        self.segment.rules = {"card_ids": [u1.card_id, u2.card_id]}
        self.segment.save()

        result = assign_campaign_to_customers(self.campaign.id)

        self.assertEqual(result["created_assignments"], 2)
        self.assertEqual(result["total_candidates"], 2)
        self.assertEqual(
            CustomerCampaignAssignment.objects.filter(campaign=self.campaign).count(),
            2,
        )

    def test_manual_segment_skips_promo_disabled(self):
        u1 = self._create_user(2001)
        u2 = self._create_user(2002, promo_enabled=False)
        self.segment.rules = {"card_ids": [u1.card_id, u2.card_id]}
        self.segment.save()

        result = assign_campaign_to_customers(self.campaign.id)

        self.assertEqual(result["created_assignments"], 1)
        self.assertEqual(result["skipped_opted_out"], 1)
        self.assertFalse(
            CustomerCampaignAssignment.objects.filter(
                campaign=self.campaign, customer=u2
            ).exists()
        )

    def test_manual_segment_no_duplicates_on_rerun(self):
        u1 = self._create_user(3001)
        self.segment.rules = {"card_ids": [u1.card_id]}
        self.segment.save()

        result1 = assign_campaign_to_customers(self.campaign.id)
        result2 = assign_campaign_to_customers(self.campaign.id)

        self.assertEqual(result1["created_assignments"], 1)
        self.assertEqual(result2["created_assignments"], 0)
        self.assertEqual(result2["skipped_existing"], 1)
        self.assertEqual(
            CustomerCampaignAssignment.objects.filter(campaign=self.campaign).count(),
            1,
        )

    # --- rule_based segment ---

    def test_rule_based_total_spent_gte(self):
        u1 = self._create_user(4001, total_spent=Decimal("5000"))
        self._create_user(4002, total_spent=Decimal("100"))

        segment = CustomerSegment.objects.create(
            name="High Spenders",
            slug="high-spenders",
            segment_type="rule_based",
            rules={"total_spent_gte": 1000},
        )
        self.campaign.segment = segment
        self.campaign.save()

        result = assign_campaign_to_customers(self.campaign.id)

        self.assertEqual(result["created_assignments"], 1)
        self.assertTrue(
            CustomerCampaignAssignment.objects.filter(
                campaign=self.campaign, customer=u1
            ).exists()
        )

    def test_rule_based_purchase_count_gte(self):
        u1 = self._create_user(5001, purchase_count=10)
        self._create_user(5002, purchase_count=1)

        segment = CustomerSegment.objects.create(
            name="Frequent Buyers",
            slug="frequent-buyers",
            segment_type="rule_based",
            rules={"purchase_count_gte": 5},
        )
        self.campaign.segment = segment
        self.campaign.save()

        result = assign_campaign_to_customers(self.campaign.id)

        self.assertEqual(result["created_assignments"], 1)
        self.assertTrue(
            CustomerCampaignAssignment.objects.filter(
                campaign=self.campaign, customer=u1
            ).exists()
        )

    def test_rule_based_bonuses_gte(self):
        u1 = self._create_user(6001, bonuses=Decimal("500"))
        self._create_user(6002, bonuses=Decimal("10"))

        segment = CustomerSegment.objects.create(
            name="Bonus Rich",
            slug="bonus-rich",
            segment_type="rule_based",
            rules={"bonuses_gte": 200},
        )
        self.campaign.segment = segment
        self.campaign.save()

        result = assign_campaign_to_customers(self.campaign.id)

        self.assertEqual(result["created_assignments"], 1)
        self.assertTrue(
            CustomerCampaignAssignment.objects.filter(
                campaign=self.campaign, customer=u1
            ).exists()
        )

    def test_rule_based_registration_date_lte(self):
        old_date = self.now - timedelta(days=365)
        new_date = self.now - timedelta(days=5)

        u1 = self._create_user(7001, registration_date=old_date)
        self._create_user(7002, registration_date=new_date)

        cutoff = (self.now - timedelta(days=30)).strftime("%Y-%m-%d")
        segment = CustomerSegment.objects.create(
            name="Old Users",
            slug="old-users",
            segment_type="rule_based",
            rules={"registration_date_lte": cutoff},
        )
        self.campaign.segment = segment
        self.campaign.save()

        result = assign_campaign_to_customers(self.campaign.id)

        self.assertEqual(result["created_assignments"], 1)
        self.assertTrue(
            CustomerCampaignAssignment.objects.filter(
                campaign=self.campaign, customer=u1
            ).exists()
        )

    def test_rule_based_invalid_date_raises_validation_error(self):
        self._create_user(8001)

        segment = CustomerSegment.objects.create(
            name="Bad Date",
            slug="bad-date",
            segment_type="rule_based",
            rules={"last_purchase_date_lte": "not-a-date"},
        )
        self.campaign.segment = segment
        self.campaign.save()

        with self.assertRaises(ValidationError):
            assign_campaign_to_customers(self.campaign.id)

    # --- campaign state checks ---

    def test_inactive_campaign_raises_error(self):
        self.campaign.is_active = False
        self.campaign.save()

        with self.assertRaises(CampaignError):
            assign_campaign_to_customers(self.campaign.id)

    def test_campaign_outside_period_raises_error(self):
        self.campaign.start_at = self.now + timedelta(days=10)
        self.campaign.end_at = self.now + timedelta(days=20)
        self.campaign.save()

        with self.assertRaises(CampaignError):
            assign_campaign_to_customers(self.campaign.id)
