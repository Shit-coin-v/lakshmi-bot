"""Integration tests for receipt + campaign reward flow."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings as django_settings
from django.utils import timezone

from apps.common import security
from apps.main.models import CustomUser
from apps.campaigns.models import (
    Campaign,
    CampaignRule,
    CustomerCampaignAssignment,
    CustomerSegment,
    CampaignRewardLog,
)
from apps.api.tests.base import OneCTestBase


@patch("apps.common.security._ip_allowed", return_value=True)
class ReceiptCampaignIntegrationTests(OneCTestBase):
    def setUp(self):
        super().setUp()
        django_settings.ONEC_API_KEY = self.API_KEY

        # Guest user required by receipt endpoint
        self.guest, _ = CustomUser.objects.update_or_create(
            telegram_id=django_settings.GUEST_TELEGRAM_ID,
            defaults={"full_name": "Гость"},
        )

        self.now = timezone.now()
        self.user = CustomUser.objects.create(telegram_id=70001)

        self.segment = CustomerSegment.objects.create(
            name="Receipt Seg", slug="receipt-seg",
            segment_type="manual",
            rules={"user_ids": [self.user.id]},
        )
        self.campaign = Campaign.objects.create(
            name="Receipt Campaign", slug="receipt-campaign",
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

    def _post_receipt(self, payload, idem_key=None):
        if idem_key is None:
            idem_key = str(uuid.uuid4())
        return self.client.post(
            "/onec/receipt",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=security.API_KEY,
            HTTP_X_IDEMPOTENCY_KEY=idem_key,
        )

    def _receipt_payload(self, receipt_guid=None):
        if receipt_guid is None:
            receipt_guid = f"R-{uuid.uuid4().hex[:12]}"
        return {
            "receipt_guid": receipt_guid,
            "datetime": "2026-03-26T12:00:00+00:00",
            "store_id": "1",
            "customer": {"card_id": self.user.card_id},
            "positions": [
                {
                    "product_code": "SKU-1",
                    "quantity": "1",
                    "price": "500.00",
                    "line_number": 1,
                    "bonus_earned": "5.00",
                },
            ],
            "totals": {
                "total_amount": "500.00",
                "discount_total": "0",
                "bonus_spent": "0",
                "bonus_earned": "5.00",
            },
        }

    # --- 1. matching_receipt_enqueues_task ---

    @patch("apps.integrations.onec.tasks.send_campaign_reward_to_onec.delay")
    def test_matching_receipt_enqueues_task(self, mock_delay, _mock_ip):
        payload = self._receipt_payload()

        with self.captureOnCommitCallbacks(execute=True):
            resp = self._post_receipt(payload)

        self.assertIn(resp.status_code, (200, 201))
        self.assertTrue(
            CampaignRewardLog.objects.filter(
                receipt_guid=payload["receipt_guid"],
                status=CampaignRewardLog.Status.PENDING,
            ).exists()
        )
        mock_delay.assert_called_once()

    # --- 2. non_matching_receipt_no_task ---

    @patch("apps.integrations.onec.tasks.send_campaign_reward_to_onec.delay")
    def test_non_matching_receipt_no_task(self, mock_delay, _mock_ip):
        # Remove assignment so campaign doesn't match
        self.assignment.delete()

        payload = self._receipt_payload()

        with self.captureOnCommitCallbacks(execute=True):
            resp = self._post_receipt(payload)

        self.assertIn(resp.status_code, (200, 201))
        self.assertFalse(
            CampaignRewardLog.objects.filter(receipt_guid=payload["receipt_guid"]).exists()
        )
        mock_delay.assert_not_called()

    # --- 3. success_log_blocks_duplicate ---

    @patch("apps.integrations.onec.tasks.send_campaign_reward_to_onec.delay")
    def test_success_log_blocks_duplicate(self, mock_delay, _mock_ip):
        receipt_guid = f"R-{uuid.uuid4().hex[:12]}"
        CampaignRewardLog.objects.create(
            receipt_guid=receipt_guid,
            customer=self.user,
            assignment=self.assignment,
            campaign=self.campaign,
            rule=self.rule,
            reward_type="fixed_bonus",
            bonus_amount=Decimal("100"),
            status=CampaignRewardLog.Status.SUCCESS,
        )
        payload = self._receipt_payload(receipt_guid=receipt_guid)

        with self.captureOnCommitCallbacks(execute=True):
            resp = self._post_receipt(payload)

        self.assertIn(resp.status_code, (200, 201))
        mock_delay.assert_not_called()

    # --- 4. pending_log_re_enqueues ---

    @patch("apps.integrations.onec.tasks.send_campaign_reward_to_onec.delay")
    def test_pending_log_re_enqueues(self, mock_delay, _mock_ip):
        receipt_guid = f"R-{uuid.uuid4().hex[:12]}"
        CampaignRewardLog.objects.create(
            receipt_guid=receipt_guid,
            customer=self.user,
            assignment=self.assignment,
            campaign=self.campaign,
            rule=self.rule,
            reward_type="fixed_bonus",
            bonus_amount=Decimal("100"),
            status=CampaignRewardLog.Status.PENDING,
        )
        payload = self._receipt_payload(receipt_guid=receipt_guid)

        with self.captureOnCommitCallbacks(execute=True):
            resp = self._post_receipt(payload)

        self.assertIn(resp.status_code, (200, 201))
        mock_delay.assert_called_once()

    # --- 5. failed_log_re_enqueues ---

    @patch("apps.integrations.onec.tasks.send_campaign_reward_to_onec.delay")
    def test_failed_log_re_enqueues(self, mock_delay, _mock_ip):
        receipt_guid = f"R-{uuid.uuid4().hex[:12]}"
        CampaignRewardLog.objects.create(
            receipt_guid=receipt_guid,
            customer=self.user,
            assignment=self.assignment,
            campaign=self.campaign,
            rule=self.rule,
            reward_type="fixed_bonus",
            bonus_amount=Decimal("100"),
            status=CampaignRewardLog.Status.FAILED,
        )
        payload = self._receipt_payload(receipt_guid=receipt_guid)

        with self.captureOnCommitCallbacks(execute=True):
            resp = self._post_receipt(payload)

        self.assertIn(resp.status_code, (200, 201))
        mock_delay.assert_called_once()

    # --- 6. guest_receipt_no_campaign ---

    @patch("apps.integrations.onec.tasks.send_campaign_reward_to_onec.delay")
    def test_guest_receipt_no_campaign(self, mock_delay, _mock_ip):
        payload = self._receipt_payload()
        payload["customer"] = {}  # no card_id → guest
        payload["totals"]["bonus_earned"] = "0"  # guest doesn't earn bonuses

        with self.captureOnCommitCallbacks(execute=True):
            resp = self._post_receipt(payload)

        self.assertIn(resp.status_code, (200, 201))
        self.assertFalse(
            CampaignRewardLog.objects.filter(receipt_guid=payload["receipt_guid"]).exists()
        )
        mock_delay.assert_not_called()

    # --- 7. receipt_response_unchanged ---

    @patch("apps.integrations.onec.tasks.send_campaign_reward_to_onec.delay")
    def test_receipt_response_unchanged(self, mock_delay, _mock_ip):
        payload = self._receipt_payload()

        with self.captureOnCommitCallbacks(execute=True):
            resp = self._post_receipt(payload)

        self.assertIn(resp.status_code, (200, 201))
        data = resp.json()
        # Verify standard response keys are present
        expected_keys = {"status", "receipt_guid", "created_count", "allocations", "customer", "totals"}
        self.assertTrue(expected_keys.issubset(data.keys()), f"Missing keys: {expected_keys - data.keys()}")
        # campaign_reward should NOT be in response
        self.assertNotIn("campaign_reward", data)

    # --- 8. campaign_error_does_not_break_receipt ---

    @patch("apps.campaigns.services.evaluate_campaign_reward", side_effect=Exception("boom"))
    @patch("apps.integrations.onec.tasks.send_campaign_reward_to_onec.delay")
    def test_campaign_error_does_not_break_receipt(self, mock_delay, mock_eval, _mock_ip):
        payload = self._receipt_payload()

        with self.captureOnCommitCallbacks(execute=True):
            resp = self._post_receipt(payload)

        self.assertIn(resp.status_code, (200, 201))
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        mock_delay.assert_not_called()
