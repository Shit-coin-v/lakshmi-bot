"""Tests for RFM-segment audience in campaigns."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.main.models import CustomUser
from apps.rfm.models import CustomerRFMProfile

from ..models import Campaign, CustomerCampaignAssignment, CustomerSegment
from ..services import assign_campaign_to_customers


class RFMAudienceTests(TestCase):
    def setUp(self):
        self.now = timezone.now()

    def _create_user(self, telegram_id, **kwargs):
        defaults = {"telegram_id": telegram_id, "promo_enabled": True}
        defaults.update(kwargs)
        return CustomUser.objects.create(**defaults)

    def _create_rfm_profile(self, customer, segment_label, rfm_code="555"):
        return CustomerRFMProfile.objects.create(
            customer=customer,
            segment_label=segment_label,
            rfm_code=rfm_code,
            r_score=5, f_score=5, m_score=5,
            calculated_at=self.now,
        )

    def _create_rfm_campaign(self, rfm_segment, **kwargs):
        defaults = {
            "name": f"RFM {rfm_segment}",
            "slug": f"rfm-{rfm_segment}",
            "audience_type": "rfm_segment",
            "rfm_segment": rfm_segment,
            "push_title": "Title",
            "push_body": "Body",
            "start_at": self.now - timedelta(days=1),
            "end_at": self.now + timedelta(days=1),
            "is_active": True,
        }
        defaults.update(kwargs)
        return Campaign.objects.create(**defaults)

    # --- RFM audience collection ---

    def test_rfm_campaign_collects_matching_customers(self):
        u1 = self._create_user(11001)
        u2 = self._create_user(11002)
        u3 = self._create_user(11003)
        self._create_rfm_profile(u1, "champions")
        self._create_rfm_profile(u2, "champions")
        self._create_rfm_profile(u3, "loyal", rfm_code="553")

        campaign = self._create_rfm_campaign("champions")
        result = assign_campaign_to_customers(campaign.id)

        self.assertEqual(result["created_assignments"], 2)
        assigned_ids = set(
            CustomerCampaignAssignment.objects.filter(campaign=campaign)
            .values_list("customer_id", flat=True)
        )
        self.assertEqual(assigned_ids, {u1.id, u2.id})

    def test_rfm_campaign_skips_promo_disabled(self):
        u1 = self._create_user(12001)
        u2 = self._create_user(12002, promo_enabled=False)
        self._create_rfm_profile(u1, "at_risk", rfm_code="355")
        self._create_rfm_profile(u2, "at_risk", rfm_code="355")

        campaign = self._create_rfm_campaign("at_risk")
        result = assign_campaign_to_customers(campaign.id)

        self.assertEqual(result["created_assignments"], 1)
        self.assertEqual(result["skipped_opted_out"], 1)

    # --- Snapshot: audience is fixed at assignment time ---

    def test_audience_snapshot_not_affected_by_rfm_update(self):
        """After assignment, changing RFM profile does not affect existing assignments."""
        u1 = self._create_user(13001)
        profile = self._create_rfm_profile(u1, "champions")

        campaign = self._create_rfm_campaign("champions")
        result = assign_campaign_to_customers(campaign.id)
        self.assertEqual(result["created_assignments"], 1)

        # RFM updates: no longer champions
        profile.segment_label = "lost"
        profile.rfm_code = "111"
        profile.save()

        # Assignment still exists
        self.assertTrue(
            CustomerCampaignAssignment.objects.filter(
                campaign=campaign, customer=u1
            ).exists()
        )

        # Re-run doesn't create new (existing assignment stays)
        result2 = assign_campaign_to_customers(campaign.id)
        self.assertEqual(result2["created_assignments"], 0)
        self.assertEqual(result2["skipped_existing"], 0)  # u1 no longer in candidates

    # --- CustomerSegment still works ---

    def test_customer_segment_campaign_still_works(self):
        u1 = self._create_user(14001)
        segment = CustomerSegment.objects.create(
            name="Manual Seg", slug="manual-seg",
            segment_type="manual",
            rules={"user_ids": [u1.id]},
        )
        campaign = Campaign.objects.create(
            name="CS Campaign", slug="cs-campaign",
            audience_type="customer_segment",
            segment=segment,
            push_title="T", push_body="B",
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=1),
            is_active=True,
        )
        result = assign_campaign_to_customers(campaign.id)
        self.assertEqual(result["created_assignments"], 1)

    # --- Validation ---

    def test_rfm_campaign_without_rfm_segment_fails_validation(self):
        with self.assertRaises(ValidationError):
            Campaign(
                name="Bad", slug="bad-rfm",
                audience_type="rfm_segment",
                rfm_segment="",
                push_title="T", push_body="B",
                start_at=self.now, end_at=self.now + timedelta(days=1),
            ).full_clean()

    def test_customer_segment_campaign_without_segment_fails_validation(self):
        with self.assertRaises(ValidationError):
            Campaign(
                name="Bad", slug="bad-cs",
                audience_type="customer_segment",
                segment=None,
                push_title="T", push_body="B",
                start_at=self.now, end_at=self.now + timedelta(days=1),
            ).full_clean()

    def test_rfm_campaign_with_segment_set_fails_validation(self):
        segment = CustomerSegment.objects.create(
            name="S", slug="s-conflict", segment_type="manual", rules={"user_ids": []},
        )
        with self.assertRaises(ValidationError):
            Campaign(
                name="Bad", slug="bad-conflict",
                audience_type="rfm_segment",
                rfm_segment="champions",
                segment=segment,
                push_title="T", push_body="B",
                start_at=self.now, end_at=self.now + timedelta(days=1),
            ).full_clean()

    def test_customer_segment_with_rfm_set_fails_validation(self):
        segment = CustomerSegment.objects.create(
            name="S2", slug="s2-conflict", segment_type="manual", rules={"user_ids": []},
        )
        with self.assertRaises(ValidationError):
            Campaign(
                name="Bad", slug="bad-conflict2",
                audience_type="customer_segment",
                rfm_segment="champions",
                segment=segment,
                push_title="T", push_body="B",
                start_at=self.now, end_at=self.now + timedelta(days=1),
            ).full_clean()

    # --- Overlapping protection works for RFM campaigns too ---

    def test_overlapping_protection_for_rfm_campaigns(self):
        u1 = self._create_user(15001)
        self._create_rfm_profile(u1, "champions")

        campaign1 = self._create_rfm_campaign("champions", slug="rfm-champ-1")
        assign_campaign_to_customers(campaign1.id)

        campaign2 = self._create_rfm_campaign("champions", slug="rfm-champ-2")
        result = assign_campaign_to_customers(campaign2.id)

        self.assertEqual(result["created_assignments"], 0)
        self.assertEqual(result["skipped_overlapping"], 1)
