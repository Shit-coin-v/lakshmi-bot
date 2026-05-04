from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff
from apps.main.models import Category, Product


class CategoryListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dairy = Category.objects.create(
            name="Молочные", external_id="01", sort_order=0, is_active=True,
        )
        cls.bread = Category.objects.create(
            name="Хлеб", external_id="02", sort_order=1, is_active=True,
        )
        Product.objects.create(
            name="Молоко", price=Decimal("100"), category=cls.dairy,
            is_active=True, store_id=1, product_code="P-001",
        )
        Product.objects.create(
            name="Кефир", price=Decimal("90"), category=cls.dairy,
            is_active=True, store_id=1, product_code="P-002",
        )
        Product.objects.create(
            name="Багет", price=Decimal("60"), category=cls.bread,
            is_active=True, store_id=1, product_code="P-003",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())
        self.url = reverse("crm_api:categories-list")

    def test_list_returns_categories_with_skus_count(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # Note: response.data — plain list (без пагинации)
        by_slug = {c["slug"]: c for c in response.data}
        self.assertIn("cat-01", by_slug)
        self.assertEqual(by_slug["cat-01"]["skus"], 2)
        self.assertEqual(by_slug["cat-02"]["skus"], 1)

    def test_list_returns_plain_array(self):
        response = self.client.get(self.url)
        # Без пагинации: response.data — список, не dict с "results"
        self.assertIsInstance(response.data, list)

    def test_stub_fields_present(self):
        response = self.client.get(self.url)
        first = response.data[0]
        for f in ("revenue", "cogs", "share", "turnover", "abc", "xyz", "trend"):
            self.assertIn(f, first)


class CategoryDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dairy = Category.objects.create(
            name="Молочные", external_id="01", sort_order=0, is_active=True,
        )
        Product.objects.create(
            name="Молоко", price=Decimal("100"), category=cls.dairy,
            is_active=True, store_id=1, product_code="P-DET-001",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())

    def test_detail_returns_skus(self):
        url = reverse("crm_api:categories-detail", kwargs={"slug": "cat-01"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slug"], "cat-01")
        self.assertEqual(len(response.data["skuList"]), 1)

    def test_detail_404_for_unknown(self):
        url = reverse("crm_api:categories-detail", kwargs={"slug": "cat-no-such"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "Категория не найдена")
