"""Tests for send_campaign_reward_to_onec Celery task."""

from decimal import Decimal
from unittest.mock import patch, MagicMock
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.main.models import CustomUser
from apps.campaigns.models import (
    Campaign,
    CampaignRule,
    CustomerCampaignAssignment,
    CustomerSegment,
    CampaignRewardLog,
)
from apps.integrations.onec.tasks import send_campaign_reward_to_onec


_TEST_SETTINGS = {
    "CACHES": {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    "CELERY_TASK_ALWAYS_EAGER": True,
    "CELERY_TASK_EAGER_PROPAGATES": True,
}


@override_settings(**_TEST_SETTINGS)
class SendCampaignRewardToOnecTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = CustomUser.objects.create(telegram_id=60001)

        self.segment = CustomerSegment.objects.create(
            name="Reward Seg", slug="reward-seg",
            segment_type="manual",
            rules={"card_ids": [self.user.card_id]},
        )
        self.campaign = Campaign.objects.create(
            name="Reward Campaign", slug="reward-campaign",
            segment=self.segment,
            push_title="T", push_body="B",
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=1),
            is_active=True, priority=100,
        )
        self.rule = CampaignRule.objects.create(
            campaign=self.campaign,
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
            is_active=True,
        )
        self.assignment = CustomerCampaignAssignment.objects.create(
            customer=self.user, campaign=self.campaign,
        )
        self.log = CampaignRewardLog.objects.create(
            receipt_guid="TASK-GUID-001",
            customer=self.user,
            assignment=self.assignment,
            campaign=self.campaign,
            rule=self.rule,
            reward_type="fixed_bonus",
            bonus_amount=Decimal("100.00"),
            is_accrual=True,
            status=CampaignRewardLog.Status.PENDING,
        )

    # --- 1. successful_send ---

    @patch("apps.integrations.onec.onec_client.send_bonus_to_onec")
    @patch("apps.integrations.onec.onec_client.get_onec_bonus_url", return_value="http://1c.local/bonus")
    def test_successful_send(self, _mock_url, mock_send):
        mock_send.return_value = {"status": "ok", "new_balance": 650.0}

        result = send_campaign_reward_to_onec.apply(args=[self.log.id]).result

        self.assertEqual(result["status"], "sent")
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CampaignRewardLog.Status.SUCCESS)
        self.assertEqual(self.log.attempts, 1)
        # Verify customer balance updated from 1C response
        self.user.refresh_from_db()
        self.assertEqual(self.user.bonuses, Decimal("650.00"))

    # --- 2. one_time_marks_used ---

    @patch("apps.integrations.onec.onec_client.send_bonus_to_onec")
    @patch("apps.integrations.onec.onec_client.get_onec_bonus_url", return_value="http://1c.local/bonus")
    def test_one_time_marks_used(self, _mock_url, mock_send):
        mock_send.return_value = {"status": "ok"}
        self.campaign.one_time_use = True
        self.campaign.save(update_fields=["one_time_use"])

        send_campaign_reward_to_onec.apply(args=[self.log.id])

        self.assignment.refresh_from_db()
        self.assertTrue(self.assignment.used)
        self.assertEqual(self.assignment.receipt_id, "TASK-GUID-001")

    # --- 3. non_one_time_not_marked ---

    @patch("apps.integrations.onec.onec_client.send_bonus_to_onec")
    @patch("apps.integrations.onec.onec_client.get_onec_bonus_url", return_value="http://1c.local/bonus")
    def test_non_one_time_not_marked(self, _mock_url, mock_send):
        mock_send.return_value = {"status": "ok"}
        self.campaign.one_time_use = False
        self.campaign.save(update_fields=["one_time_use"])

        send_campaign_reward_to_onec.apply(args=[self.log.id])

        self.assignment.refresh_from_db()
        self.assertFalse(self.assignment.used)

    # --- 4. onec_error_no_used ---

    @patch("apps.integrations.onec.onec_client.send_bonus_to_onec", side_effect=RuntimeError("1C down"))
    @patch("apps.integrations.onec.onec_client.get_onec_bonus_url", return_value="http://1c.local/bonus")
    def test_onec_error_no_used(self, _mock_url, mock_send):
        self.campaign.one_time_use = True
        self.campaign.save(update_fields=["one_time_use"])

        result = send_campaign_reward_to_onec.apply(args=[self.log.id]).result

        self.assertEqual(result["status"], "failed")
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CampaignRewardLog.Status.FAILED)
        self.assignment.refresh_from_db()
        self.assertFalse(self.assignment.used)

    # --- 5. already_success_skipped ---

    @patch("apps.integrations.onec.onec_client.send_bonus_to_onec")
    @patch("apps.integrations.onec.onec_client.get_onec_bonus_url", return_value="http://1c.local/bonus")
    def test_already_success_skipped(self, _mock_url, mock_send):
        self.log.status = CampaignRewardLog.Status.SUCCESS
        self.log.save(update_fields=["status"])

        result = send_campaign_reward_to_onec.apply(args=[self.log.id]).result

        self.assertEqual(result["status"], "already_sent")
        mock_send.assert_not_called()

    # --- 6. url_not_configured ---

    @patch("apps.integrations.onec.onec_client.get_onec_bonus_url", return_value=None)
    def test_url_not_configured(self, _mock_url):
        result = send_campaign_reward_to_onec.apply(args=[self.log.id]).result

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "no_url")

    # --- 7. payload_format ---

    @patch("apps.integrations.onec.onec_client.send_bonus_to_onec")
    @patch("apps.integrations.onec.onec_client.get_onec_bonus_url", return_value="http://1c.local/bonus")
    def test_payload_format(self, _mock_url, mock_send):
        mock_send.return_value = {"status": "ok"}

        send_campaign_reward_to_onec.apply(args=[self.log.id])

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        self.assertEqual(call_kwargs["card_id"], self.user.card_id)
        self.assertEqual(call_kwargs["bonus_amount"], Decimal("100.00"))
        self.assertTrue(call_kwargs["is_accrual"])
        self.assertEqual(call_kwargs["receipt_guid"], self.log.receipt_guid)

    # --- 8. retry_on_error (non-eager mode) ---

    @patch("apps.integrations.onec.onec_client.send_bonus_to_onec", side_effect=RuntimeError("timeout"))
    @patch("apps.integrations.onec.onec_client.get_onec_bonus_url", return_value="http://1c.local/bonus")
    def test_retry_on_error_marks_failed_in_eager(self, _mock_url, mock_send):
        """In eager mode task catches error and returns failed (no actual retry).
        Verify log status and last_error are set correctly."""
        result = send_campaign_reward_to_onec.apply(args=[self.log.id]).result

        self.assertEqual(result["status"], "failed")
        self.assertIn("timeout", result["reason"])
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CampaignRewardLog.Status.FAILED)
        self.assertIn("timeout", self.log.last_error)
        self.assertEqual(self.log.attempts, 1)
