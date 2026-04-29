from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.common.authentication import generate_tokens
from apps.main.models import Category, CustomUser, Product
from apps.showcase.models import ProductRanking


class ProductListOrderingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.now = timezone.now()

        self.cat = Category.objects.create(name="Молочные")

        # 4 товара: 2 в наличии, 2 нет.
        self.p_in_high = Product.objects.create(
            name="Молоко 3.2%", price=Decimal("89"), stock=Decimal("10"),
            category=self.cat, store_id=1, is_active=True,
        )
        self.p_in_low = Product.objects.create(
            name="Кефир 1%", price=Decimal("75"), stock=Decimal("5"),
            category=self.cat, store_id=1, is_active=True,
        )
        self.p_oos_high = Product.objects.create(
            name="Сыр", price=Decimal("320"), stock=Decimal("0"),
            category=self.cat, store_id=1, is_active=True,
        )
        self.p_oos_low = Product.objects.create(
            name="Йогурт", price=Decimal("55"), stock=Decimal("0"),
            category=self.cat, store_id=1, is_active=True,
        )

        for product, score in [
            (self.p_in_high, 2.0),
            (self.p_in_low, 5.0),
            (self.p_oos_high, 10.0),
            (self.p_oos_low, 1.0),
        ]:
            ProductRanking.objects.create(
                customer=None, product=product, score=score,
                calculated_at=self.now,
            )

    def _get_ids(self, response):
        # ProductListSerializer выдаёт `id` = integer PK модели.
        return [item["id"] for item in response.json()]

    def test_anonymous_orders_in_stock_first_then_by_global_score(self):
        response = self.client.get(
            f"/api/products/?category_id={self.cat.pk}",
        )
        self.assertEqual(response.status_code, 200)
        ids = self._get_ids(response)
        # in_stock сначала, в группе — по score убыванию
        self.assertEqual(
            ids,
            [
                self.p_in_low.id,
                self.p_in_high.id,
                self.p_oos_high.id,
                self.p_oos_low.id,
            ],
        )

    @override_settings(PERSONAL_RANKING_ENABLED=True)
    def test_authenticated_uses_personal_ranking(self):
        customer = CustomUser.objects.create(telegram_id=70001)
        # personal score переопределяет global для p_in_high
        ProductRanking.objects.create(
            customer=customer, product=self.p_in_high, score=999.0,
            calculated_at=self.now,
        )
        tokens = generate_tokens(customer)
        response = self.client.get(
            f"/api/products/?category_id={self.cat.pk}",
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        self.assertEqual(response.status_code, 200)
        ids = self._get_ids(response)
        # p_in_high теперь первый (personal score=999 > p_in_low global=5)
        self.assertEqual(ids[0], self.p_in_high.id)

    @override_settings(PERSONAL_RANKING_ENABLED=False)
    def test_kill_switch_off_uses_only_global(self):
        customer = CustomUser.objects.create(telegram_id=70002)
        ProductRanking.objects.create(
            customer=customer, product=self.p_oos_low, score=999.0,
            calculated_at=self.now,
        )
        tokens = generate_tokens(customer)
        response = self.client.get(
            f"/api/products/?category_id={self.cat.pk}",
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        self.assertEqual(response.status_code, 200)
        ids = self._get_ids(response)
        # kill-switch выключен — personal score игнорируется, p_oos_low всё ещё последний
        self.assertEqual(ids[-1], self.p_oos_low.id)


class ProductListPaginationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = Category.objects.create(name="Big")

        # 25 активных товаров
        self.products = [
            Product.objects.create(
                name=f"P{i:02d}",
                price=Decimal("1"),
                stock=Decimal("1"),
                category=self.cat,
                store_id=1,
                is_active=True,
            )
            for i in range(25)
        ]

    def test_link_header_has_next_when_more_pages(self):
        response = self.client.get(
            f"/api/products/?category_id={self.cat.pk}&page_size=10",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 10)
        link = response.headers.get("Link", "")
        self.assertIn('rel="next"', link)

    def test_link_header_no_next_on_last_page(self):
        response = self.client.get(
            f"/api/products/?category_id={self.cat.pk}&page_size=10&page=3",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 5)  # 25 - 20 = 5
        link = response.headers.get("Link", "")
        self.assertNotIn('rel="next"', link)

    def test_total_count_header(self):
        response = self.client.get(
            f"/api/products/?category_id={self.cat.pk}&page_size=10",
        )
        self.assertEqual(response.headers.get("X-Total-Count"), "25")
