"""Unit tests for evaluate_campaign_reward() service."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.main.models import CustomUser, Product, Category
from apps.campaigns.models import (
    Campaign,
    CampaignRule,
    CustomerCampaignAssignment,
    CustomerSegment,
    CampaignRewardLog,
)
from apps.campaigns.services import evaluate_campaign_reward


class EvaluateCampaignRewardTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = CustomUser.objects.create(telegram_id=50001)
        # user gets card_id auto-generated in save()

        self.segment = CustomerSegment.objects.create(
            name="Test Seg",
            slug="test-seg",
            segment_type="manual",
            rules={"card_ids": [self.user.card_id]},
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            slug="test-campaign",
            segment=self.segment,
            push_title="T",
            push_body="B",
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=1),
            is_active=True,
            priority=100,
        )
        self.rule = CampaignRule.objects.create(
            campaign=self.campaign,
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
            is_active=True,
        )
        self.assignment = CustomerCampaignAssignment.objects.create(
            customer=self.user,
            campaign=self.campaign,
        )
        self.positions = [
            {
                "product_code": "P1",
                "quantity": "2",
                "price": "500.00",
                "discount_amount": "0",
            },
        ]
        self.total_amount = Decimal("1000.00")
        self.receipt_guid = "TEST-GUID-001"

    def _evaluate(self, **kwargs):
        defaults = {
            "customer": self.user,
            "total_amount": self.total_amount,
            "positions": self.positions,
            "receipt_guid": self.receipt_guid,
        }
        defaults.update(kwargs)
        return evaluate_campaign_reward(**defaults)

    def _replace_rule(self, **kwargs):
        """Deactivate old rule and create a new one."""
        self.rule.is_active = False
        self.rule.save()
        self.rule = CampaignRule.objects.create(
            campaign=self.campaign,
            is_active=True,
            **kwargs,
        )

    # --- 1. fixed_bonus_no_filter ---

    def test_fixed_bonus_no_filter(self):
        result = self._evaluate()
        self.assertIsNotNone(result)
        self.assertEqual(result.bonus_amount, Decimal("100.00"))

    # --- 2. bonus_percent_no_filter ---

    def test_bonus_percent_no_filter(self):
        self._replace_rule(
            reward_type="bonus_percent",
            reward_percent=Decimal("10"),
        )
        result = self._evaluate(total_amount=Decimal("5000.00"))
        self.assertIsNotNone(result)
        self.assertEqual(result.bonus_amount, Decimal("500.00"))

    # --- 3. fixed_plus_percent ---

    def test_fixed_plus_percent(self):
        self._replace_rule(
            reward_type="fixed_plus_percent",
            reward_value=Decimal("50"),
            reward_percent=Decimal("5"),
        )
        result = self._evaluate(total_amount=Decimal("2000.00"))
        self.assertIsNotNone(result)
        self.assertEqual(result.bonus_amount, Decimal("150.00"))

    # --- 4. product_discount_skipped ---

    def test_product_discount_skipped(self):
        self.rule.is_active = False
        self.rule.save()
        # product_discount requires product filter; create with legacy FK to pass clean()
        product = Product.objects.create(
            name="Test", product_code="P1", price=Decimal("100"),
            store_id=1, one_c_guid="guid-1",
        )
        self.rule = CampaignRule.objects.create(
            campaign=self.campaign,
            reward_type="product_discount",
            reward_value=Decimal("50"),
            product=product,
            is_active=True,
        )
        result = self._evaluate()
        self.assertIsNone(result)

    # --- 5. min_purchase_not_met ---

    def test_min_purchase_not_met(self):
        self._replace_rule(
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
            min_purchase_amount=Decimal("2000"),
        )
        result = self._evaluate(total_amount=Decimal("1000.00"))
        self.assertIsNone(result)

    # --- 6. min_purchase_met ---

    def test_min_purchase_met(self):
        self._replace_rule(
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
            min_purchase_amount=Decimal("500"),
        )
        result = self._evaluate(total_amount=Decimal("1000.00"))
        self.assertIsNotNone(result)
        self.assertEqual(result.bonus_amount, Decimal("100.00"))

    # --- 7. products_m2m_match ---

    def test_products_m2m_match(self):
        product = Product.objects.create(
            name="Match", product_code="P1", price=Decimal("500"),
            store_id=1, one_c_guid="guid-m2m",
        )
        self._replace_rule(
            reward_type="fixed_bonus",
            reward_value=Decimal("200"),
        )
        self.rule.products.add(product)

        positions = [
            {"product_code": "P1", "quantity": "2", "price": "500.00", "discount_amount": "0"},
            {"product_code": "P2", "quantity": "1", "price": "300.00", "discount_amount": "0"},
        ]
        result = self._evaluate(positions=positions, total_amount=Decimal("1300.00"))
        self.assertIsNotNone(result)
        self.assertEqual(result.bonus_amount, Decimal("200.00"))

    # --- 8. products_m2m_no_match ---

    def test_products_m2m_no_match(self):
        product = Product.objects.create(
            name="NoMatch", product_code="X99", price=Decimal("500"),
            store_id=1, one_c_guid="guid-x99",
        )
        self._replace_rule(
            reward_type="fixed_bonus",
            reward_value=Decimal("200"),
        )
        self.rule.products.add(product)

        result = self._evaluate()
        self.assertIsNone(result)

    # --- 9. category_match ---

    def test_category_match(self):
        cat = Category.objects.create(name="Молочка", external_id="CAT-001")
        Product.objects.create(
            name="Молоко", product_code="P1", price=Decimal("100"),
            store_id=1, category=cat,
        )
        self._replace_rule(
            reward_type="fixed_bonus",
            reward_value=Decimal("75"),
            category=cat,
        )
        result = self._evaluate()
        self.assertIsNotNone(result)
        self.assertEqual(result.bonus_amount, Decimal("75.00"))

    # --- 10. category_no_match ---

    def test_category_no_match(self):
        cat = Category.objects.create(name="Хлеб", external_id="CAT-002")
        # No product with code P1 in this category
        Product.objects.create(
            name="Батон", product_code="BREAD-1", price=Decimal("50"),
            store_id=1, category=cat,
        )
        self._replace_rule(
            reward_type="fixed_bonus",
            reward_value=Decimal("75"),
            category=cat,
        )
        result = self._evaluate()
        self.assertIsNone(result)

    # --- 11. legacy_product_fk ---

    def test_legacy_product_fk(self):
        product = Product.objects.create(
            name="Legacy", product_code="P1", price=Decimal("500"),
            store_id=1, one_c_guid="guid-legacy",
        )
        self._replace_rule(
            reward_type="fixed_bonus",
            reward_value=Decimal("60"),
            product=product,
        )
        result = self._evaluate()
        self.assertIsNotNone(result)
        self.assertEqual(result.bonus_amount, Decimal("60.00"))

    # --- 12. no_assignment ---

    def test_no_assignment(self):
        self.assignment.delete()
        result = self._evaluate()
        self.assertIsNone(result)

    # --- 13. used_assignment ---

    def test_used_assignment(self):
        self.assignment.used = True
        self.assignment.save()
        result = self._evaluate()
        self.assertIsNone(result)

    # --- 14. inactive_campaign ---

    def test_inactive_campaign(self):
        self.campaign.is_active = False
        self.campaign.save(update_fields=["is_active"])
        result = self._evaluate()
        self.assertIsNone(result)

    # --- 15. expired_campaign ---

    def test_expired_campaign(self):
        self.campaign.end_at = self.now - timedelta(hours=1)
        self.campaign.save(update_fields=["end_at"])
        result = self._evaluate()
        self.assertIsNone(result)

    # --- 16. not_started_campaign ---

    def test_not_started_campaign(self):
        self.campaign.start_at = self.now + timedelta(hours=1)
        self.campaign.save(update_fields=["start_at"])
        result = self._evaluate()
        self.assertIsNone(result)

    # --- 17. no_active_rule ---

    def test_no_active_rule(self):
        self.rule.is_active = False
        self.rule.save()
        result = self._evaluate()
        self.assertIsNone(result)

    # --- 18. already_success_receipt ---

    def test_already_success_receipt(self):
        CampaignRewardLog.objects.create(
            receipt_guid=self.receipt_guid,
            customer=self.user,
            assignment=self.assignment,
            campaign=self.campaign,
            rule=self.rule,
            reward_type="fixed_bonus",
            bonus_amount=Decimal("100"),
            status=CampaignRewardLog.Status.SUCCESS,
        )
        result = self._evaluate()
        self.assertIsNone(result)

    # --- 19. no_card_id ---

    def test_no_card_id(self):
        user_no_card = CustomUser.objects.create(telegram_id=50099)
        # Force remove card_id
        CustomUser.objects.filter(pk=user_no_card.pk).update(card_id=None)
        user_no_card.refresh_from_db()

        CustomerCampaignAssignment.objects.create(
            customer=user_no_card, campaign=self.campaign,
        )
        result = self._evaluate(customer=user_no_card)
        self.assertIsNone(result)

    # --- 20. percent_on_matching_only ---

    def test_percent_on_matching_only(self):
        product = Product.objects.create(
            name="Target", product_code="P1", price=Decimal("500"),
            store_id=1, one_c_guid="guid-target",
        )
        self._replace_rule(
            reward_type="bonus_percent",
            reward_percent=Decimal("10"),
        )
        self.rule.products.add(product)

        positions = [
            {"product_code": "P1", "quantity": "2", "price": "500.00", "discount_amount": "0"},
            {"product_code": "P2", "quantity": "1", "price": "300.00", "discount_amount": "0"},
        ]
        # P1: (500-0)*2 = 1000, 10% = 100
        result = self._evaluate(positions=positions, total_amount=Decimal("1300.00"))
        self.assertIsNotNone(result)
        self.assertEqual(result.bonus_amount, Decimal("100.00"))

    # --- 21. multiple_assignments_fail_closed ---

    def test_multiple_assignments_fail_closed(self):
        segment2 = CustomerSegment.objects.create(
            name="Seg2", slug="seg2", segment_type="manual",
            rules={"card_ids": [self.user.card_id]},
        )
        campaign2 = Campaign.objects.create(
            name="Campaign 2", slug="campaign-2",
            segment=segment2,
            push_title="T2", push_body="B2",
            start_at=self.now - timedelta(days=1),
            end_at=self.now + timedelta(days=1),
            is_active=True, priority=50,
        )
        CampaignRule.objects.create(
            campaign=campaign2,
            reward_type="fixed_bonus",
            reward_value=Decimal("50"),
            is_active=True,
        )
        CustomerCampaignAssignment.objects.create(
            customer=self.user, campaign=campaign2,
        )
        result = self._evaluate()
        self.assertIsNone(result)
