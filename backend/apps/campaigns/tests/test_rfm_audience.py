"""Tests for RFM-segment audience in campaigns."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.main.models import CustomUser
from apps.rfm.constants import AT_RISK, CHAMPIONS, LOYAL
from apps.rfm.models import CustomerRFMProfile

from ..models import AudienceType, Campaign, CustomerCampaignAssignment, CustomerSegment
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
            "audience_type": AudienceType.RFM_SEGMENT,
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
        self._create_rfm_profile(u1, CHAMPIONS)
        self._create_rfm_profile(u2, CHAMPIONS)
        self._create_rfm_profile(u3, LOYAL, rfm_code="553")

        campaign = self._create_rfm_campaign(CHAMPIONS)
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
        self._create_rfm_profile(u1, AT_RISK, rfm_code="355")
        self._create_rfm_profile(u2, AT_RISK, rfm_code="355")

        campaign = self._create_rfm_campaign(AT_RISK)
        result = assign_campaign_to_customers(campaign.id)

        self.assertEqual(result["created_assignments"], 1)
        self.assertEqual(result["skipped_opted_out"], 1)

    # --- Snapshot: audience is fixed at assignment time ---

    def test_audience_snapshot_not_affected_by_rfm_update(self):
        """After assignment, changing RFM profile does not affect existing assignments."""
        u1 = self._create_user(13001)
        profile = self._create_rfm_profile(u1, CHAMPIONS)

        campaign = self._create_rfm_campaign(CHAMPIONS)
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
            audience_type=AudienceType.CUSTOMER_SEGMENT,
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
                audience_type=AudienceType.RFM_SEGMENT,
                rfm_segment="",
                push_title="T", push_body="B",
                start_at=self.now, end_at=self.now + timedelta(days=1),
            ).full_clean()

    def test_customer_segment_campaign_without_segment_fails_validation(self):
        with self.assertRaises(ValidationError):
            Campaign(
                name="Bad", slug="bad-cs",
                audience_type=AudienceType.CUSTOMER_SEGMENT,
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
                audience_type=AudienceType.RFM_SEGMENT,
                rfm_segment=CHAMPIONS,
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
                audience_type=AudienceType.CUSTOMER_SEGMENT,
                rfm_segment=CHAMPIONS,
                segment=segment,
                push_title="T", push_body="B",
                start_at=self.now, end_at=self.now + timedelta(days=1),
            ).full_clean()

    # --- Overlapping protection works for RFM campaigns too ---

    def test_overlapping_protection_for_rfm_campaigns(self):
        u1 = self._create_user(15001)
        self._create_rfm_profile(u1, CHAMPIONS)

        campaign1 = self._create_rfm_campaign(CHAMPIONS, slug="rfm-champ-1")
        assign_campaign_to_customers(campaign1.id)

        campaign2 = self._create_rfm_campaign(CHAMPIONS, slug="rfm-champ-2")
        result = assign_campaign_to_customers(campaign2.id)

        self.assertEqual(result["created_assignments"], 0)
        self.assertEqual(result["skipped_overlapping"], 1)

    # --- Active campaign rule for RFM ---

    def test_active_campaign_blocks_rfm_customer_from_new_campaign(self):
        """Client with active RFM campaign must not be assigned to another."""
        u1 = self._create_user(16001)
        self._create_rfm_profile(u1, CHAMPIONS)

        c1 = self._create_rfm_campaign(CHAMPIONS, slug="rfm-active-1")
        assign_campaign_to_customers(c1.id)
        self.assertTrue(
            CustomerCampaignAssignment.objects.filter(campaign=c1, customer=u1).exists()
        )

        # Second campaign: champions again — same period
        c2 = self._create_rfm_campaign(CHAMPIONS, slug="rfm-active-3")
        result = assign_campaign_to_customers(c2.id)
        self.assertEqual(result["created_assignments"], 0)
        self.assertEqual(result["skipped_overlapping"], 1)

    # --- Backward compatibility: old campaigns with segment ---

    def test_old_campaign_with_segment_works_after_migration(self):
        """Campaign created with segment (old style) should still work."""
        u1 = self._create_user(17001)
        segment = CustomerSegment.objects.create(
            name="Legacy Seg", slug="legacy-seg",
            segment_type="manual",
            rules={"user_ids": [u1.id]},
        )
        campaign = Campaign.objects.create(
            name="Legacy Campaign", slug="legacy-campaign",
            segment=segment,
            push_title="T", push_body="B",
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=1),
            is_active=True,
        )
        self.assertEqual(campaign.audience_type, AudienceType.CUSTOMER_SEGMENT)
        self.assertIsNone(campaign.rfm_segment)

        result = assign_campaign_to_customers(campaign.id)
        self.assertEqual(result["created_assignments"], 1)
        self.assertTrue(
            CustomerCampaignAssignment.objects.filter(
                campaign=campaign, customer=u1,
            ).exists()
        )


class DBConstraintTests(TransactionTestCase):
    """Verify CheckConstraints at the database level, bypassing model clean()."""

    def setUp(self):
        self.now = timezone.now()
        self.table = connection.ops.quote_name(Campaign._meta.db_table)
        self.segment = CustomerSegment.objects.create(
            name="DBTest", slug="dbtest", segment_type="manual", rules={"user_ids": []},
        )

    def _insert_raw(self, audience_type, segment_id, rfm_segment):
        """Insert directly via SQL, bypassing model save()/clean()."""
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {self.table}
                    (name, slug, audience_type, segment_id, rfm_segment,
                     push_title, push_body, start_at, end_at,
                     one_time_use, priority, is_active, created_at, updated_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    "raw", f"raw-{audience_type}-{rfm_segment or 'none'}-{segment_id or 'none'}",
                    audience_type, segment_id, rfm_segment or "",
                    "T", "B", self.now, self.now + timedelta(days=1),
                    False, 100, True, self.now, self.now,
                ],
            )

    def test_db_rejects_cs_without_segment(self):
        with self.assertRaises(IntegrityError):
            self._insert_raw(AudienceType.CUSTOMER_SEGMENT, None, None)

    def test_db_rejects_cs_with_rfm_set(self):
        with self.assertRaises(IntegrityError):
            self._insert_raw(AudienceType.CUSTOMER_SEGMENT, self.segment.id, CHAMPIONS)

    def test_db_rejects_rfm_without_rfm_segment(self):
        with self.assertRaises(IntegrityError):
            self._insert_raw(AudienceType.RFM_SEGMENT, None, None)

    def test_db_rejects_rfm_with_segment_set(self):
        with self.assertRaises(IntegrityError):
            self._insert_raw(AudienceType.RFM_SEGMENT, self.segment.id, CHAMPIONS)

    def test_db_accepts_valid_cs_campaign(self):
        self._insert_raw(AudienceType.CUSTOMER_SEGMENT, self.segment.id, None)

    def test_db_accepts_valid_rfm_campaign(self):
        self._insert_raw(AudienceType.RFM_SEGMENT, None, CHAMPIONS)

    # --- enum value constraints ---

    def test_db_rejects_invalid_audience_type(self):
        with self.assertRaises(IntegrityError):
            self._insert_raw("foo", self.segment.id, None)

    def test_db_rejects_invalid_rfm_segment_value(self):
        with self.assertRaises(IntegrityError):
            self._insert_raw(AudienceType.RFM_SEGMENT, None, "nonexistent_segment")
