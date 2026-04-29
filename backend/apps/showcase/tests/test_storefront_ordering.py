from decimal import Decimal
from unittest.mock import Mock

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.main.models import Category, CustomUser, Product
from apps.showcase.models import ProductRanking
from apps.showcase.services import apply_storefront_ordering


class _AnonRequest:
    """Заменитель request для анонимного юзера: user без is_authenticated."""

    def __init__(self):
        self.user = Mock(spec=[])  # не CustomUser


class ApplyStorefrontOrderingTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        cat = Category.objects.create(name="Test")

        # Создаём 4 товара — порядок создания важен для проверки tie-breaker по pk.
        self.p_in_high = Product.objects.create(
            name="A", price=Decimal("10"), stock=Decimal("10"),
            category=cat, store_id=1,
        )
        self.p_in_low = Product.objects.create(
            name="B", price=Decimal("10"), stock=Decimal("5"),
            category=cat, store_id=1,
        )
        self.p_oos_high = Product.objects.create(
            name="C", price=Decimal("10"), stock=Decimal("0"),
            category=cat, store_id=1,
        )
        self.p_oos_low = Product.objects.create(
            name="D", price=Decimal("10"), stock=Decimal("0"),
            category=cat, store_id=1,
        )

        # Глобальные рейтинги
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

    def test_anonymous_uses_only_global_ranking(self):
        """В наличии — наверх; внутри групп — по global score."""
        result = list(apply_storefront_ordering(
            Product.objects.all(), _AnonRequest(),
        ))

        self.assertEqual(result[0], self.p_in_low)   # in_stock + 5.0
        self.assertEqual(result[1], self.p_in_high)  # in_stock + 2.0
        self.assertEqual(result[2], self.p_oos_high) # oos + 10.0
        self.assertEqual(result[3], self.p_oos_low)  # oos + 1.0

    @override_settings(PERSONAL_RANKING_ENABLED=True)
    def test_authenticated_personal_overrides_global(self):
        """Personal score переопределяет global для конкретного юзера."""
        user = CustomUser.objects.create(telegram_id=42001)
        ProductRanking.objects.create(
            customer=user, product=self.p_in_high, score=999.0,
            calculated_at=self.now,
        )

        request = Mock()
        request.user = user

        result = list(apply_storefront_ordering(
            Product.objects.all(), request,
        ))

        # in_high теперь первый из-за personal 999.0
        self.assertEqual(result[0], self.p_in_high)
        self.assertEqual(result[1], self.p_in_low)

    @override_settings(PERSONAL_RANKING_ENABLED=False)
    def test_kill_switch_disables_personal_ranking(self):
        """Когда флаг выключен — personal ranking игнорируется."""
        user = CustomUser.objects.create(telegram_id=42002)
        ProductRanking.objects.create(
            customer=user, product=self.p_oos_low, score=999.0,
            calculated_at=self.now,
        )

        request = Mock()
        request.user = user

        result = list(apply_storefront_ordering(
            Product.objects.all(), request,
        ))

        # oos_low — последний (по global 1.0), не первый
        self.assertEqual(result[3], self.p_oos_low)

    def test_tie_breaker_by_pk(self):
        """При равных in_stock и score — сортировка по pk."""
        cat = Category.objects.first()

        # Два товара, одинаковый stock, одинаковый score
        same_a = Product.objects.create(
            name="SameA", price=Decimal("1"), stock=Decimal("1"),
            category=cat, store_id=1,
        )
        same_b = Product.objects.create(
            name="SameB", price=Decimal("1"), stock=Decimal("1"),
            category=cat, store_id=1,
        )
        for p in [same_a, same_b]:
            ProductRanking.objects.create(
                customer=None, product=p, score=0.0,
                calculated_at=self.now,
            )

        result = list(apply_storefront_ordering(
            Product.objects.filter(pk__in=[same_a.pk, same_b.pk]),
            _AnonRequest(),
        ))
        # Порядок по pk — same_a создан раньше → первый.
        self.assertEqual([p.pk for p in result], [same_a.pk, same_b.pk])

    def test_no_ranking_records_score_zero(self):
        """Товар без записи в ProductRanking — score=0, идёт в конце группы."""
        cat = Category.objects.first()
        no_rank = Product.objects.create(
            name="NoRank", price=Decimal("1"), stock=Decimal("1"),
            category=cat, store_id=1,
        )

        result = list(apply_storefront_ordering(
            Product.objects.filter(stock__gt=0),
            _AnonRequest(),
        ))
        # no_rank (score=0) должен быть последним из in-stock группы
        self.assertEqual(result[-1], no_rank)
