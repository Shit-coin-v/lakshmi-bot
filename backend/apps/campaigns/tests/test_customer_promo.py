"""Тесты GET /api/campaigns/customer-promo/ endpoint."""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.campaigns.models import (
    Campaign,
    CampaignRule,
    CustomerCampaignAssignment,
    CustomerSegment,
)
from apps.main.models import Category, CustomUser, Product
from apps.rfm.models import CustomerBonusTier

URL = "/api/campaigns/customer-promo/"
API_KEY = "test-key-12345"


@override_settings(INTEGRATION_API_KEY=API_KEY)
class CustomerPromoViewTests(TestCase):

    def setUp(self):
        self.now = timezone.now()
        self.today = date.today()
        self.user = CustomUser.objects.create(telegram_id=300001)
        self.segment = CustomerSegment.objects.create(
            name="Test Seg", slug="test-seg",
        )

    def _headers(self):
        return {"HTTP_X_API_KEY": API_KEY}

    def _create_tier(self, user=None, tier="standard"):
        user = user or self.user
        # Используем today ± 1 день, чтобы запись всегда покрывала текущую дату.
        # Раньше фиксировали 1—28 число месяца, что ломало тесты 29—31 числа.
        return CustomerBonusTier.objects.create(
            customer=user,
            tier=tier,
            segment_label_at_fixation=tier,
            effective_from=self.today - timedelta(days=1),
            effective_to=self.today + timedelta(days=1),
        )

    def _create_campaign(self, slug="c1", **kwargs):
        defaults = {
            "name": f"Campaign {slug}",
            "slug": slug,
            "segment": self.segment,
            "push_title": "t",
            "push_body": "b",
            "start_at": self.now - timedelta(days=1),
            "end_at": self.now + timedelta(days=30),
            "is_active": True,
        }
        defaults.update(kwargs)
        return Campaign.objects.create(**defaults)

    def _create_rule(self, campaign, **kwargs):
        defaults = {
            "campaign": campaign,
            "reward_type": "fixed_bonus",
            "reward_value": Decimal("150"),
            "stacking_mode": "stack_with_base",
            "is_active": True,
        }
        defaults.update(kwargs)
        return CampaignRule.objects.create(**defaults)

    def _assign(self, campaign, user=None, **kwargs):
        user = user or self.user
        return CustomerCampaignAssignment.objects.create(
            customer=user, campaign=campaign, **kwargs,
        )

    # --- Auth ---

    def test_no_api_key_403(self):
        resp = self.client.get(URL, {"telegram_id": "300001"})
        self.assertEqual(resp.status_code, 403)

    def test_wrong_api_key_403(self):
        resp = self.client.get(URL, {"telegram_id": "300001"}, HTTP_X_API_KEY="wrong")
        self.assertEqual(resp.status_code, 403)

    # --- Validation ---

    def test_no_telegram_id_400(self):
        resp = self.client.get(URL, **self._headers())
        self.assertEqual(resp.status_code, 400)

    def test_non_numeric_telegram_id_400(self):
        resp = self.client.get(URL, {"telegram_id": "abc"}, **self._headers())
        self.assertEqual(resp.status_code, 400)

    # --- Customer not found ---

    def test_customer_not_found(self):
        resp = self.client.get(URL, {"telegram_id": "999999"}, **self._headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["found"])
        self.assertIsNone(data["bonus_tier"])

    # --- Bonus tier ---

    def test_tier_champions(self):
        self._create_tier(tier="champions")
        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        data = resp.json()
        self.assertTrue(data["found"])
        self.assertEqual(data["bonus_tier"], "champions")
        self.assertIsNotNone(data["bonus_tier_effective_from"])
        self.assertIsNotNone(data["bonus_tier_effective_to"])

    def test_tier_standard(self):
        self._create_tier(tier="standard")
        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        data = resp.json()
        self.assertEqual(data["bonus_tier"], "standard")

    def test_no_tier_fallback_standard(self):
        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        data = resp.json()
        self.assertEqual(data["bonus_tier"], "standard")
        self.assertIsNone(data["bonus_tier_effective_from"])

    def test_tier_champions_rfm_changed(self):
        """Tier=champions стабилен, даже если RFM изменился."""
        self._create_tier(tier="champions")
        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        self.assertEqual(resp.json()["bonus_tier"], "champions")

    # --- Campaign: no assignment ---

    def test_no_assignment_campaign_null(self):
        self._create_tier()
        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        self.assertIsNone(resp.json()["campaign"])

    # --- Campaign: normal flow ---

    def test_active_assignment_fixed_bonus(self):
        self._create_tier()
        camp = self._create_campaign()
        self._create_rule(camp)
        self._assign(camp)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        data = resp.json()
        self.assertIsNotNone(data["campaign"])
        self.assertEqual(data["campaign"]["reward_type"], "fixed_bonus")
        self.assertEqual(float(data["campaign"]["reward_value"]), 150.00)

    def test_active_assignment_bonus_percent(self):
        self._create_tier()
        camp = self._create_campaign()
        self._create_rule(
            camp, reward_type="bonus_percent",
            reward_value=Decimal("0"), reward_percent=Decimal("10"),
        )
        self._assign(camp)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        data = resp.json()["campaign"]
        self.assertEqual(float(data["reward_percent"]), 10.00)

    # --- Campaign: one_time_use ---

    def test_one_time_use_used_excluded(self):
        self._create_tier()
        camp = self._create_campaign(one_time_use=True)
        self._create_rule(camp)
        self._assign(camp, used=True, used_at=self.now)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        self.assertIsNone(resp.json()["campaign"])

    def test_reusable_used_included(self):
        self._create_tier()
        camp = self._create_campaign(one_time_use=False)
        self._create_rule(camp)
        self._assign(camp, used=True, used_at=self.now)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        self.assertIsNotNone(resp.json()["campaign"])

    # --- Campaign: expired / future ---

    def test_expired_campaign_null(self):
        self._create_tier()
        camp = self._create_campaign(
            end_at=self.now - timedelta(hours=1),
        )
        self._create_rule(camp)
        self._assign(camp)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        self.assertIsNone(resp.json()["campaign"])

    def test_future_campaign_null(self):
        self._create_tier()
        camp = self._create_campaign(
            start_at=self.now + timedelta(days=1),
        )
        self._create_rule(camp)
        self._assign(camp)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        self.assertIsNone(resp.json()["campaign"])

    # --- Fail-closed ---

    def test_zero_active_rules_campaign_null(self):
        self._create_tier()
        camp = self._create_campaign()
        # Правило не создаём — 0 active rules
        self._assign(camp)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        self.assertIsNone(resp.json()["campaign"])

    def test_multiple_active_assignments_fail_closed(self):
        self._create_tier()
        camp1 = self._create_campaign(slug="c1")
        camp2 = self._create_campaign(slug="c2")
        self._create_rule(camp1)
        self._create_rule(camp2)
        self._assign(camp1)
        self._assign(camp2)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        self.assertIsNone(resp.json()["campaign"])

    def test_replace_base_fail_closed(self):
        self._create_tier()
        camp = self._create_campaign()
        # Обходим валидацию clean() для теста
        rule = CampaignRule(
            campaign=camp,
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
            stacking_mode="replace_base",
            is_active=True,
        )
        CampaignRule.objects.bulk_create([rule])

        self._assign(camp)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        self.assertIsNone(resp.json()["campaign"])

    def test_product_without_one_c_guid_fail_closed(self):
        self._create_tier()
        product = Product.objects.create(name="No GUID", one_c_guid=None, price="10.00", store_id=1)
        camp = self._create_campaign()
        rule = CampaignRule(
            campaign=camp,
            reward_type="product_discount",
            reward_value=Decimal("50"),
            product=product,
            is_active=True,
        )
        CampaignRule.objects.bulk_create([rule])
        self._assign(camp)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        self.assertIsNone(resp.json()["campaign"])

    def test_category_without_external_id_fail_closed(self):
        self._create_tier()
        cat = Category.objects.create(name="No ExtID", external_id=None)
        camp = self._create_campaign()
        rule = CampaignRule(
            campaign=camp,
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
            category=cat,
            is_active=True,
        )
        CampaignRule.objects.bulk_create([rule])
        self._assign(camp)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        self.assertIsNone(resp.json()["campaign"])

    def test_legacy_product_plus_products_m2m_fail_closed(self):
        """legacy product + products M2M одновременно → fail-closed, campaign: null + WARNING."""
        self._create_tier()
        p1 = Product.objects.create(name="P1", one_c_guid="g-fc1", price="10.00", store_id=1)
        p2 = Product.objects.create(name="P2", one_c_guid="g-fc2", price="10.00", store_id=1)
        camp = self._create_campaign()
        # Обходим валидацию: bulk_create + ручное добавление M2M
        rule = CampaignRule(
            campaign=camp,
            reward_type="product_discount",
            reward_value=Decimal("50"),
            product=p1,
            is_active=True,
        )
        CampaignRule.objects.bulk_create([rule])
        rule = CampaignRule.objects.get(pk=rule.pk)
        rule.products.add(p2)
        self._assign(camp)

        with self.assertLogs("apps.campaigns.views", level="WARNING") as cm:
            resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())

        self.assertIsNone(resp.json()["campaign"])
        log_output = "\n".join(cm.output)
        self.assertIn(f"rule_id={rule.id}", log_output)
        self.assertIn(f"campaign_id={camp.id}", log_output)
        self.assertIn("legacy product", log_output)
        self.assertIn("products M2M", log_output)
        self.assertIn("fail-closed", log_output)

    # --- Conditions ---

    def test_conditions_min_purchase_amount(self):
        self._create_tier()
        camp = self._create_campaign()
        self._create_rule(camp, min_purchase_amount=Decimal("1000"))
        self._assign(camp)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        conds = resp.json()["campaign"]["conditions"]
        self.assertEqual(float(conds["min_purchase_amount"]), 1000.00)

    def test_conditions_product(self):
        self._create_tier()
        product = Product.objects.create(
            name="Молоко", one_c_guid="guid-milk", price="10.00", store_id=1,
        )
        camp = self._create_campaign()
        self._create_rule(camp, product=product, reward_type="product_discount")
        self._assign(camp)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        conds = resp.json()["campaign"]["conditions"]
        self.assertEqual(conds["product"]["one_c_guid"], "guid-milk")

    def test_conditions_category(self):
        self._create_tier()
        cat = Category.objects.create(name="Молочка", external_id="cat-dairy")
        camp = self._create_campaign()
        rule = CampaignRule(
            campaign=camp,
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
            category=cat,
            is_active=True,
        )
        CampaignRule.objects.bulk_create([rule])
        self._assign(camp)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        conds = resp.json()["campaign"]["conditions"]
        self.assertEqual(conds["category"]["external_id"], "cat-dairy")

    # --- bonus_tier + campaign одновременно ---

    def test_both_tier_and_campaign(self):
        self._create_tier(tier="champions")
        camp = self._create_campaign()
        self._create_rule(camp)
        self._assign(camp)

        resp = self.client.get(URL, {"telegram_id": "300001"}, **self._headers())
        data = resp.json()
        self.assertEqual(data["bonus_tier"], "champions")
        self.assertIsNotNone(data["campaign"])
