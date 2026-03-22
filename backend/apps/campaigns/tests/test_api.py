from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.main.models import CustomUser

from ..models import Campaign, CampaignRule, CustomerCampaignAssignment, CustomerSegment

URL = "/api/campaigns/active/"


class UserAssignedCampaignsAPITestCase(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.segment = CustomerSegment.objects.create(
            name="Test Segment",
            slug="test-segment",
            segment_type="manual",
            rules={"user_ids": []},
        )
        self.user = CustomUser.objects.create(
            telegram_id=70001,
            full_name="API User",
        )

    def _auth_headers(self, user=None):
        u = user or self.user
        return {"HTTP_X_TELEGRAM_USER_ID": str(u.telegram_id)}

    def _create_campaign(self, slug, **kwargs):
        defaults = {
            "name": f"Campaign {slug}",
            "slug": slug,
            "segment": self.segment,
            "push_title": "Title",
            "push_body": "Body",
            "start_at": self.now - timedelta(days=1),
            "end_at": self.now + timedelta(days=1),
            "is_active": True,
        }
        defaults.update(kwargs)
        return Campaign.objects.create(**defaults)

    def _assign(self, campaign, user=None, **kwargs):
        return CustomerCampaignAssignment.objects.create(
            customer=user or self.user,
            campaign=campaign,
            **kwargs,
        )

    # --- основные сценарии ---

    def test_returns_own_assignments(self):
        c = self._create_campaign("own-1")
        self._assign(c)

        resp = self.client.get(URL, **self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["campaign"]["slug"], "own-1")

    def test_other_user_assignments_not_visible(self):
        other = CustomUser.objects.create(telegram_id=70002, full_name="Other")
        c = self._create_campaign("other-1")
        self._assign(c, user=other)

        resp = self.client.get(URL, **self._auth_headers())

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 0)

    # --- фильтрация по состоянию кампании ---

    def test_inactive_campaign_excluded(self):
        c = self._create_campaign("inactive-1", is_active=False)
        self._assign(c)

        resp = self.client.get(URL, **self._auth_headers())

        self.assertEqual(len(resp.json()), 0)

    def test_campaign_before_start_excluded(self):
        c = self._create_campaign(
            "future-1",
            start_at=self.now + timedelta(days=10),
            end_at=self.now + timedelta(days=20),
        )
        self._assign(c)

        resp = self.client.get(URL, **self._auth_headers())

        self.assertEqual(len(resp.json()), 0)

    def test_campaign_after_end_excluded(self):
        c = self._create_campaign(
            "expired-1",
            start_at=self.now - timedelta(days=20),
            end_at=self.now - timedelta(days=10),
        )
        self._assign(c)

        resp = self.client.get(URL, **self._auth_headers())

        self.assertEqual(len(resp.json()), 0)

    # --- one_time_use + used ---

    def test_one_time_use_used_excluded(self):
        c = self._create_campaign("otu-used", one_time_use=True)
        self._assign(c, used=True, used_at=self.now)

        resp = self.client.get(URL, **self._auth_headers())

        self.assertEqual(len(resp.json()), 0)

    def test_one_time_use_not_used_included(self):
        c = self._create_campaign("otu-fresh", one_time_use=True)
        self._assign(c)

        resp = self.client.get(URL, **self._auth_headers())

        self.assertEqual(len(resp.json()), 1)

    def test_reusable_used_included(self):
        c = self._create_campaign("reusable-1", one_time_use=False)
        self._assign(c, used=True, used_at=self.now)

        resp = self.client.get(URL, **self._auth_headers())

        self.assertEqual(len(resp.json()), 1)

    # --- вложенные rules ---

    def test_rules_nested_in_response(self):
        c = self._create_campaign("with-rules")
        CampaignRule.objects.create(
            campaign=c,
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
        )
        self._assign(c)

        resp = self.client.get(URL, **self._auth_headers())
        data = resp.json()

        self.assertEqual(len(data), 1)
        rules = data[0]["campaign"]["rules"]
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["reward_type"], "fixed_bonus")

    def test_inactive_rules_excluded(self):
        c = self._create_campaign("inactive-rule")
        CampaignRule.objects.create(
            campaign=c,
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
            is_active=True,
        )
        CampaignRule.objects.create(
            campaign=c,
            reward_type="bonus_percent",
            reward_percent=Decimal("5.00"),
            is_active=False,
        )
        self._assign(c)

        resp = self.client.get(URL, **self._auth_headers())
        rules = resp.json()[0]["campaign"]["rules"]

        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["reward_type"], "fixed_bonus")

    # --- сортировка ---

    def test_sorted_by_priority_and_created_at(self):
        c_low = self._create_campaign("low-prio", priority=10)
        c_high = self._create_campaign("high-prio", priority=200)
        c_mid = self._create_campaign("mid-prio", priority=100)
        self._assign(c_low)
        self._assign(c_high)
        self._assign(c_mid)

        resp = self.client.get(URL, **self._auth_headers())
        slugs = [item["campaign"]["slug"] for item in resp.json()]

        self.assertEqual(slugs, ["high-prio", "mid-prio", "low-prio"])

    # --- assignment-поля в ответе ---

    def test_assignment_fields_in_response(self):
        c = self._create_campaign("fields-check")
        self._assign(c)

        resp = self.client.get(URL, **self._auth_headers())
        item = resp.json()[0]

        self.assertIn("assigned_at", item)
        self.assertIn("used", item)
        self.assertIn("used_at", item)
        self.assertIn("push_sent", item)
        self.assertIn("push_sent_at", item)
        self.assertIn("campaign", item)

    # --- авторизация ---

    def test_unauthenticated_returns_401(self):
        resp = self.client.get(URL)

        self.assertEqual(resp.status_code, 401)
