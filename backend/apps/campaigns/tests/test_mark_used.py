"""Тесты POST /api/campaigns/mark-used/ endpoint."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.campaigns.models import (
    Campaign,
    CampaignRule,
    CustomerCampaignAssignment,
    CustomerSegment,
)
from apps.main.models import CustomUser

URL = "/api/campaigns/mark-used/"
API_KEY = "test-key-12345"


@override_settings(INTEGRATION_API_KEY=API_KEY)
class MarkCampaignUsedViewTests(TestCase):

    def setUp(self):
        self.now = timezone.now()
        self.user = CustomUser.objects.create(telegram_id=400001)
        self.segment = CustomerSegment.objects.create(name="S", slug="s")
        self.campaign = Campaign.objects.create(
            name="C", slug="c-mark", segment=self.segment,
            push_title="t", push_body="b",
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=30),
            one_time_use=True,
        )
        CampaignRule.objects.create(
            campaign=self.campaign,
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
        )
        self.assignment = CustomerCampaignAssignment.objects.create(
            customer=self.user, campaign=self.campaign,
        )

    def _headers(self):
        return {"HTTP_X_API_KEY": API_KEY, "content_type": "application/json"}

    def test_no_api_key_403(self):
        resp = self.client.post(URL, {"telegram_id": 400001, "campaign_id": self.campaign.id})
        self.assertEqual(resp.status_code, 403)

    def test_valid_mark_used(self):
        resp = self.client.post(
            URL,
            {"telegram_id": 400001, "campaign_id": self.campaign.id, "receipt_id": "r-123"},
            **self._headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assignment.refresh_from_db()
        self.assertTrue(self.assignment.used)
        self.assertIsNotNone(self.assignment.used_at)
        self.assertEqual(self.assignment.receipt_id, "r-123")

    def test_idempotent(self):
        self.assignment.used = True
        self.assignment.used_at = self.now
        self.assignment.save()

        resp = self.client.post(
            URL,
            {"telegram_id": 400001, "campaign_id": self.campaign.id},
            **self._headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["ok"], True)

    def test_customer_not_found_404(self):
        resp = self.client.post(
            URL,
            {"telegram_id": 999999, "campaign_id": self.campaign.id},
            **self._headers(),
        )
        self.assertEqual(resp.status_code, 404)

    def test_assignment_not_found_404(self):
        resp = self.client.post(
            URL,
            {"telegram_id": 400001, "campaign_id": 99999},
            **self._headers(),
        )
        self.assertEqual(resp.status_code, 404)

    def test_not_one_time_use_400(self):
        self.campaign.one_time_use = False
        self.campaign.save()

        resp = self.client.post(
            URL,
            {"telegram_id": 400001, "campaign_id": self.campaign.id},
            **self._headers(),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("not one-time-use", resp.json()["detail"])
