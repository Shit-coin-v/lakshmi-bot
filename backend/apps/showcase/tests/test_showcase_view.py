from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.common.authentication import generate_tokens
from apps.main.models import Category, CustomUser, Product
from apps.showcase.models import ProductRanking


class ShowcaseViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.now = timezone.now()

        root = Category.objects.create(name="Root", parent=None)
        dairy = Category.objects.create(name="Dairy", parent=root)

        self.p1 = Product.objects.create(
            name="AAA", price=Decimal("10"), category=dairy,
            is_active=True, store_id=1, stock=Decimal("10"),
        )
        self.p2 = Product.objects.create(
            name="BBB", price=Decimal("20"), category=dairy,
            is_active=True, store_id=1, stock=Decimal("5"),
        )
        self.p3 = Product.objects.create(
            name="CCC", price=Decimal("30"), category=dairy,
            is_active=True, store_id=1, stock=Decimal("0"),
        )

        # Global rankings: p1=300, p2=900, p3=100
        for product, score in [(self.p1, 300), (self.p2, 900), (self.p3, 100)]:
            ProductRanking.objects.create(
                customer=None, product=product, score=score,
                calculated_at=self.now,
            )

        self.customer = CustomUser.objects.create(telegram_id=5001)
        self.tokens = generate_tokens(self.customer)

    def _get(self, token=None):
        headers = {}
        if token:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return self.client.get("/api/showcase/", **headers)

    def _get_product_ids(self, response):
        return [item["id"] for item in response.json()]

    def test_anonymous_returns_global_ranking(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)
        ids = self._get_product_ids(response)
        # p2(900) > p1(300) in stock, then p3(100) out of stock
        self.assertEqual(ids, [self.p2.id, self.p1.id, self.p3.id])

    @override_settings(PERSONAL_RANKING_ENABLED=False)
    def test_kill_switch_off_returns_global(self):
        """Even with valid token, kill switch off → global ranking."""
        response = self._get(token=self.tokens["access"])
        self.assertEqual(response.status_code, 200)
        ids = self._get_product_ids(response)
        self.assertEqual(ids, [self.p2.id, self.p1.id, self.p3.id])

    @override_settings(PERSONAL_RANKING_ENABLED=True)
    def test_authenticated_without_personal_records_falls_back(self):
        """Auth user with no personal records → global fallback."""
        response = self._get(token=self.tokens["access"])
        self.assertEqual(response.status_code, 200)
        ids = self._get_product_ids(response)
        self.assertEqual(ids, [self.p2.id, self.p1.id, self.p3.id])

    @override_settings(PERSONAL_RANKING_ENABLED=True)
    def test_authenticated_with_personal_records(self):
        """Auth user with personal records gets personalized order."""
        # Personal: p1=999, p2 has no personal record (fallback to global 900)
        ProductRanking.objects.create(
            customer=self.customer, product=self.p1, score=999,
            calculated_at=self.now,
        )

        response = self._get(token=self.tokens["access"])
        self.assertEqual(response.status_code, 200)
        ids = self._get_product_ids(response)
        # In stock: p1(999 personal) > p2(900 global fallback)
        # Out of stock: p3(100 global)
        self.assertEqual(ids, [self.p1.id, self.p2.id, self.p3.id])

    @override_settings(PERSONAL_RANKING_ENABLED=True)
    def test_per_product_fallback(self):
        """Some products personal, some global fallback, mixed correctly."""
        # p1: personal score 50 (low), p2: no personal (global 900)
        ProductRanking.objects.create(
            customer=self.customer, product=self.p1, score=50,
            calculated_at=self.now,
        )
        response = self._get(token=self.tokens["access"])
        ids = self._get_product_ids(response)
        # In stock: p2(900 global fallback) > p1(50 personal)
        self.assertEqual(ids[0], self.p2.id)
        self.assertEqual(ids[1], self.p1.id)

    def test_invalid_token_returns_401(self):
        response = self._get(token="invalid.jwt.token")
        self.assertEqual(response.status_code, 401)

    def test_expired_token_returns_401(self):
        import datetime
        import jwt
        from django.conf import settings

        payload = {
            "user_id": self.customer.pk,
            "type": "access",
            "iat": datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
            "exp": datetime.datetime(2020, 1, 2, tzinfo=datetime.timezone.utc),
        }
        expired = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        response = self._get(token=expired)
        self.assertEqual(response.status_code, 401)

    def test_no_auth_header_is_anonymous_not_401(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)

    @override_settings(PERSONAL_RANKING_ENABLED=True)
    def test_no_duplicate_products(self):
        """Two JOINs should not duplicate products in response."""
        ProductRanking.objects.create(
            customer=self.customer, product=self.p1, score=500,
            calculated_at=self.now,
        )
        response = self._get(token=self.tokens["access"])
        ids = self._get_product_ids(response)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 3)
