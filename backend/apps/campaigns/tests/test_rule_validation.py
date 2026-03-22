"""Тесты валидации CampaignRule: model clean() и admin form."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.campaigns.admin import CampaignRuleAdminForm
from apps.campaigns.models import Campaign, CampaignRule, CustomerSegment
from apps.main.models import Category, Product


class CampaignRuleCleanTests(TestCase):

    def setUp(self):
        self.segment = CustomerSegment.objects.create(name="S", slug="s-val")
        self.campaign = Campaign.objects.create(
            name="C", slug="c-val", segment=self.segment,
            push_title="t", push_body="b",
            start_at=timezone.now(), end_at=timezone.now(),
        )

    def test_replace_base_rejected(self):
        rule = CampaignRule(
            campaign=self.campaign,
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
            stacking_mode="replace_base",
        )
        with self.assertRaises(ValidationError) as ctx:
            rule.full_clean()
        self.assertIn("stacking_mode", ctx.exception.message_dict)

    def test_category_without_external_id_rejected(self):
        cat = Category.objects.create(name="No ExtID", external_id=None)
        rule = CampaignRule(
            campaign=self.campaign,
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
            category=cat,
        )
        with self.assertRaises(ValidationError) as ctx:
            rule.full_clean()
        self.assertIn("category", ctx.exception.message_dict)

    def test_legacy_product_without_guid_rejected(self):
        product = Product.objects.create(name="No GUID", one_c_guid=None, price="10.00", store_id=1)
        rule = CampaignRule(
            campaign=self.campaign,
            reward_type="product_discount",
            reward_value=Decimal("50"),
            product=product,
        )
        with self.assertRaises(ValidationError) as ctx:
            rule.full_clean()
        self.assertIn("product", ctx.exception.message_dict)

    def test_legacy_product_and_category_rejected(self):
        product = Product.objects.create(name="P", one_c_guid="guid-1", price="10.00", store_id=1)
        cat = Category.objects.create(name="C", external_id="ext-1")
        rule = CampaignRule(
            campaign=self.campaign,
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
            product=product,
            category=cat,
        )
        with self.assertRaises(ValidationError) as ctx:
            rule.full_clean()
        self.assertIn("product", ctx.exception.message_dict)

    def test_product_discount_without_filter_rejected_on_existing(self):
        """product_discount без товарного фильтра на существующем объекте → ошибка."""
        # Создаём через bulk_create чтобы обойти clean()
        rule = CampaignRule(
            campaign=self.campaign,
            reward_type="product_discount",
            reward_value=Decimal("50"),
        )
        CampaignRule.objects.bulk_create([rule])
        rule = CampaignRule.objects.get(pk=rule.pk)
        with self.assertRaises(ValidationError) as ctx:
            rule.full_clean()
        self.assertIn("product", ctx.exception.message_dict)

    def test_product_discount_with_category_valid(self):
        """product_discount с category — валидно."""
        cat = Category.objects.create(name="Dairy", external_id="cat-d")
        rule = CampaignRule(
            campaign=self.campaign,
            reward_type="product_discount",
            reward_value=Decimal("50"),
            category=cat,
        )
        rule.full_clean()

    def test_category_alone_is_valid(self):
        """Category как самостоятельный товарный фильтр допустима."""
        cat = Category.objects.create(name="Dairy", external_id="cat-dairy")
        rule = CampaignRule(
            campaign=self.campaign,
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
            category=cat,
        )
        rule.full_clean()  # Не должно падать

    def test_legacy_product_as_fallback_valid(self):
        """Legacy product (deprecated FK) продолжает работать."""
        product = Product.objects.create(name="Milk", one_c_guid="guid-milk", price="10.00", store_id=1)
        rule = CampaignRule(
            campaign=self.campaign,
            reward_type="product_discount",
            reward_value=Decimal("50"),
            product=product,
        )
        rule.full_clean()  # Не должно падать

    def test_no_product_conditions_valid(self):
        """Rule без товарных условий (только min_purchase_amount) допустима."""
        rule = CampaignRule(
            campaign=self.campaign,
            reward_type="fixed_bonus",
            reward_value=Decimal("100"),
            min_purchase_amount=Decimal("1000"),
        )
        rule.full_clean()


class CampaignRuleAdminFormTests(TestCase):
    """Тесты admin form валидации, включая M2M products."""

    def setUp(self):
        self.segment = CustomerSegment.objects.create(name="S", slug="s-form")
        self.campaign = Campaign.objects.create(
            name="C", slug="c-form", segment=self.segment,
            push_title="t", push_body="b",
            start_at=timezone.now(), end_at=timezone.now(),
        )

    def test_replace_base_not_in_choices(self):
        """replace_base убран из form choices."""
        form = CampaignRuleAdminForm()
        choices = [c[0] for c in form.fields["stacking_mode"].choices]
        self.assertNotIn("replace_base", choices)

    def test_form_legacy_product_plus_products_rejected(self):
        """legacy product + products M2M одновременно → ошибка."""
        p1 = Product.objects.create(name="P1", one_c_guid="g1", price="10.00", store_id=1)
        p2 = Product.objects.create(name="P2", one_c_guid="g2", price="10.00", store_id=1)
        form = CampaignRuleAdminForm(data={
            "campaign": self.campaign.id,
            "reward_type": "product_discount",
            "reward_value": "50",
            "stacking_mode": "stack_with_base",
            "is_active": True,
            "product": p1.id,
            "products": [p2.id],
        })
        self.assertFalse(form.is_valid())
        self.assertIn("product", form.errors)

    def test_form_products_plus_category_rejected(self):
        """products M2M + category → ошибка."""
        p = Product.objects.create(name="P", one_c_guid="g", price="10.00", store_id=1)
        cat = Category.objects.create(name="C", external_id="e")
        form = CampaignRuleAdminForm(data={
            "campaign": self.campaign.id,
            "reward_type": "fixed_bonus",
            "reward_value": "100",
            "stacking_mode": "stack_with_base",
            "is_active": True,
            "products": [p.id],
            "category": cat.id,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_form_product_discount_without_filter_rejected(self):
        """product_discount без товарного фильтра → ошибка."""
        form = CampaignRuleAdminForm(data={
            "campaign": self.campaign.id,
            "reward_type": "product_discount",
            "reward_value": "50",
            "stacking_mode": "stack_with_base",
            "is_active": True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("product", form.errors)

    def test_form_product_discount_with_products_valid(self):
        """product_discount с products M2M — валидно."""
        p = Product.objects.create(name="P", one_c_guid="g-pd", price="10.00", store_id=1)
        form = CampaignRuleAdminForm(data={
            "campaign": self.campaign.id,
            "reward_type": "product_discount",
            "reward_value": "50",
            "stacking_mode": "stack_with_base",
            "is_active": True,
            "products": [p.id],
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_product_discount_with_category_valid(self):
        """product_discount с category — валидно."""
        cat = Category.objects.create(name="Dairy", external_id="cat-f")
        form = CampaignRuleAdminForm(data={
            "campaign": self.campaign.id,
            "reward_type": "product_discount",
            "reward_value": "50",
            "stacking_mode": "stack_with_base",
            "is_active": True,
            "category": cat.id,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_product_discount_with_legacy_product_valid(self):
        """product_discount с legacy product — валидно."""
        p = Product.objects.create(name="Milk", one_c_guid="g-lp", price="10.00", store_id=1)
        form = CampaignRuleAdminForm(data={
            "campaign": self.campaign.id,
            "reward_type": "product_discount",
            "reward_value": "50",
            "stacking_mode": "stack_with_base",
            "is_active": True,
            "product": p.id,
        })
        self.assertTrue(form.is_valid(), form.errors)
