"""Тесты эндпоинта списка кампаний CRM."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.campaigns.models import Campaign, CampaignRule, CustomerCampaignAssignment
from apps.crm_api.tests._factories import create_staff
from apps.main.models import CustomUser


class CampaignListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()
        cls.c1 = Campaign.objects.create(
            name="Весенний кешбэк",
            slug="spring-cb",
            audience_type="rfm_segment",
            rfm_segment="champions",
            push_title="t",
            push_body="b",
            start_at=now,
            end_at=now + timedelta(days=30),
            priority=200,
            is_active=True,
        )
        CampaignRule.objects.create(
            campaign=cls.c1, reward_type="bonus_percent", reward_percent=Decimal("7"), is_active=True,
        )
        cls.c2 = Campaign.objects.create(
            name="Старая",
            slug="old",
            audience_type="rfm_segment",
            rfm_segment="loyal",
            push_title="t", push_body="b",
            start_at=now - timedelta(days=60), end_at=now - timedelta(days=30),
            priority=100, is_active=False,
        )
        # Назначения: два разных пользователя для корректной агрегации reach=2, used=1
        u1 = CustomUser.objects.create(
            full_name="X1", phone="+71", telegram_id=180001, card_id="LC-X1-CMP",
        )
        u2 = CustomUser.objects.create(
            full_name="X2", phone="+72", telegram_id=180002, card_id="LC-X2-CMP",
        )
        CustomerCampaignAssignment.objects.create(customer=u1, campaign=cls.c1, used=False)
        CustomerCampaignAssignment.objects.create(customer=u2, campaign=cls.c1, used=True)

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())
        self.url = reverse("crm_api:campaigns-list")

    def test_list_returns_campaigns(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        ids = {c["id"] for c in response.data}
        self.assertEqual(ids, {f"CMP-{self.c1.id}", f"CMP-{self.c2.id}"})

    def test_filter_active(self):
        response = self.client.get(self.url, {"status": "active"})
        self.assertEqual({c["status"] for c in response.data}, {"active"})

    def test_reach_used_counts(self):
        response = self.client.get(self.url, {"status": "active"})
        c = response.data[0]
        self.assertEqual(c["reach"], 2)
        self.assertEqual(c["used"], 1)

    def test_rules_serialized_first(self):
        response = self.client.get(self.url, {"status": "active"})
        c = response.data[0]
        self.assertIn("7", c["rules"])

    def test_audience_field(self):
        response = self.client.get(self.url, {"status": "active"})
        c = response.data[0]
        self.assertEqual(c["audience"], "RFM: champions")
