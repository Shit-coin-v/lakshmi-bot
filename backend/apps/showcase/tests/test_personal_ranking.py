import math
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.loyalty.models import Transaction
from apps.main.models import Category, CustomUser, Product
from apps.showcase.models import ProductRanking
from apps.showcase.services import (
    CATEGORY_WEIGHT,
    GLOBAL_WEIGHT,
    PERSONAL_WEIGHT,
    REPEAT_DECAY,
    REPEAT_WEIGHT,
    _build_category_depth_map,
    calculate_all_personal_rankings,
    calculate_personal_rankings,
)


class CategoryDepthMapTests(TestCase):
    def test_flat_root_categories(self):
        """Root categories (depth 0) resolve to themselves."""
        r = Category.objects.create(name="Root", parent=None)
        result = _build_category_depth_map()
        self.assertEqual(result[r.id], r.id)

    def test_depth_1_resolves_to_self(self):
        """Depth-1 children resolve to themselves."""
        root = Category.objects.create(name="Root", parent=None)
        child = Category.objects.create(name="Child", parent=root)
        result = _build_category_depth_map()
        self.assertEqual(result[child.id], child.id)

    def test_depth_2_resolves_to_depth_1_ancestor(self):
        """Depth-2 categories resolve to their depth-1 ancestor."""
        root = Category.objects.create(name="Root", parent=None)
        mid = Category.objects.create(name="Mid", parent=root)
        leaf = Category.objects.create(name="Leaf", parent=mid)
        result = _build_category_depth_map()
        self.assertEqual(result[leaf.id], mid.id)

    def test_depth_3_resolves_to_depth_1(self):
        root = Category.objects.create(name="Root", parent=None)
        d1 = Category.objects.create(name="D1", parent=root)
        d2 = Category.objects.create(name="D2", parent=d1)
        d3 = Category.objects.create(name="D3", parent=d2)
        result = _build_category_depth_map()
        self.assertEqual(result[d3.id], d1.id)
        self.assertEqual(result[d2.id], d1.id)


class PersonalRankingCalculationTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.recent = self.now.date() - timedelta(days=10)

        # Categories: Root → Dairy, Root → Bread
        self.root = Category.objects.create(name="Root", parent=None)
        self.dairy = Category.objects.create(name="Dairy", parent=self.root)
        self.bread = Category.objects.create(name="Bread", parent=self.root)

        # Products
        self.kefir = Product.objects.create(
            name="Kefir", price=Decimal("50"), category=self.dairy,
            is_active=True, store_id=1,
        )
        self.baton = Product.objects.create(
            name="Baton", price=Decimal("30"), category=self.bread,
            is_active=True, store_id=1,
        )
        self.juice = Product.objects.create(
            name="Juice", price=Decimal("80"), category=self.dairy,
            is_active=True, store_id=1,
        )

        # Customer
        self.customer = CustomUser.objects.create(telegram_id=1001)

        # Global rankings
        ProductRanking.objects.create(
            customer=None, product=self.kefir, score=800.0,
            calculated_at=self.now,
        )
        ProductRanking.objects.create(
            customer=None, product=self.baton, score=900.0,
            calculated_at=self.now,
        )
        ProductRanking.objects.create(
            customer=None, product=self.juice, score=700.0,
            calculated_at=self.now,
        )

    def _create_txn(self, product, quantity, customer=None, date=None):
        Transaction.objects.create(
            customer=customer or self.customer,
            product=product,
            quantity=quantity,
            total_amount=Decimal("100"),
            purchase_date=date or self.recent,
            store_id=1,
        )

    def test_basic_calculation(self):
        """Customer with purchases in two categories gets correct scores."""
        # 30 units dairy (kefir) in 1 txn, 10 units bread (baton) in 1 txn = 40 total qty
        self._create_txn(self.kefir, 30)
        self._create_txn(self.baton, 10)

        stats = calculate_personal_rankings(self.customer.id)

        self.assertFalse(stats["cold_start"])
        self.assertGreater(stats["created"], 0)

        records = {
            r.product_id: r.score
            for r in ProductRanking.objects.filter(customer=self.customer)
        }

        # Kefir: cat_score = (30/40)*1000 = 750
        # times_bought = 1 (one transaction row, not qty)
        # repeat = (1-exp(-0.5*1))*1000 ≈ 393
        # personal = 750*0.7 + 393*0.3 ≈ 643
        # final = 643*0.6 + 800*0.4 ≈ 706
        self.assertIn(self.kefir.id, records)
        times_bought_kefir = 1  # one purchase event
        self.assertAlmostEqual(
            records[self.kefir.id],
            (750 * CATEGORY_WEIGHT + (1 - math.exp(-REPEAT_DECAY * times_bought_kefir)) * 1000 * REPEAT_WEIGHT) * PERSONAL_WEIGHT
            + 800 * GLOBAL_WEIGHT,
            places=1,
        )

    def test_cold_start_no_transactions(self):
        """Customer without transactions → no personal records."""
        # Pre-create some stale personal records
        ProductRanking.objects.create(
            customer=self.customer, product=self.kefir, score=500,
            calculated_at=self.now,
        )

        stats = calculate_personal_rankings(self.customer.id)

        self.assertTrue(stats["cold_start"])
        self.assertEqual(stats["deleted"], 1)
        self.assertEqual(
            ProductRanking.objects.filter(customer=self.customer).count(), 0
        )

    def test_sparse_storage_no_signal(self):
        """Products with no personal signal don't get records."""
        # Only buy kefir → juice is same category (dairy) so gets cat_score
        # baton has no signal at all (different category, never bought)
        self._create_txn(self.kefir, 5)

        calculate_personal_rankings(self.customer.id)

        personal_product_ids = set(
            ProductRanking.objects.filter(customer=self.customer)
            .values_list("product_id", flat=True)
        )
        # Kefir: has both cat_score and repeat_score
        self.assertIn(self.kefir.id, personal_product_ids)
        # Juice: same dairy category → cat_score > 0
        self.assertIn(self.juice.id, personal_product_ids)
        # Baton: bread category, never bought → both signals 0
        self.assertNotIn(self.baton.id, personal_product_ids)

    def test_product_without_category(self):
        """Product with category=NULL → category_score=0, repeat works."""
        no_cat = Product.objects.create(
            name="NoCat", price=Decimal("10"), category=None,
            is_active=True, store_id=1,
        )
        ProductRanking.objects.create(
            customer=None, product=no_cat, score=500.0,
            calculated_at=self.now,
        )

        self._create_txn(no_cat, 3)
        self._create_txn(self.kefir, 2)  # need at least one categorized product

        calculate_personal_rankings(self.customer.id)

        record = ProductRanking.objects.filter(
            customer=self.customer, product=no_cat,
        ).first()
        self.assertIsNotNone(record)

        # cat_score = 0 (no category)
        # times_bought = 1 (one txn with qty=3, but repeat counts events)
        rep = (1 - math.exp(-REPEAT_DECAY * 1)) * 1000
        personal = 0 * CATEGORY_WEIGHT + rep * REPEAT_WEIGHT
        expected = personal * PERSONAL_WEIGHT + 500 * GLOBAL_WEIGHT
        self.assertAlmostEqual(record.score, expected, places=1)

    def test_deep_category_resolved_to_depth_1(self):
        """Product in depth-2 category gets score via depth-1 ancestor."""
        leaf = Category.objects.create(name="Kefir_1pct", parent=self.dairy)
        deep_product = Product.objects.create(
            name="Kefir1", price=Decimal("55"), category=leaf,
            is_active=True, store_id=1,
        )
        ProductRanking.objects.create(
            customer=None, product=deep_product, score=600.0,
            calculated_at=self.now,
        )

        # Buy kefir (dairy) and deep_product (dairy→kefir_1pct → resolves to dairy)
        self._create_txn(self.kefir, 5)
        self._create_txn(deep_product, 3)

        calculate_personal_rankings(self.customer.id)

        record = ProductRanking.objects.filter(
            customer=self.customer, product=deep_product,
        ).first()
        self.assertIsNotNone(record)
        # deep_product resolved to dairy, all qty is in dairy → cat_score = 1000
        # both products share dairy category

    def test_null_product_transaction_ignored(self):
        """Transactions with product=NULL are excluded."""
        Transaction.objects.create(
            customer=self.customer, product=None, quantity=10,
            total_amount=Decimal("100"), purchase_date=self.recent, store_id=1,
        )
        stats = calculate_personal_rankings(self.customer.id)
        self.assertTrue(stats["cold_start"])

    def test_null_quantity_transaction_ignored(self):
        """Transactions with quantity=NULL are excluded."""
        Transaction.objects.create(
            customer=self.customer, product=self.kefir, quantity=None,
            total_amount=Decimal("100"), purchase_date=self.recent, store_id=1,
        )
        stats = calculate_personal_rankings(self.customer.id)
        self.assertTrue(stats["cold_start"])

    def test_zero_quantity_transaction_ignored(self):
        """Transactions with quantity<=0 are excluded."""
        Transaction.objects.create(
            customer=self.customer, product=self.kefir, quantity=0,
            total_amount=Decimal("100"), purchase_date=self.recent, store_id=1,
        )
        stats = calculate_personal_rankings(self.customer.id)
        self.assertTrue(stats["cold_start"])

    def test_repeat_score_counts_events_not_quantity(self):
        """repeat_score must depend on purchase event count, not sum of quantity.

        Scenario A: 1 txn with qty=5 → times_bought=1
        Scenario B: 5 txns with qty=1 → times_bought=5
        Same total qty, but B must have higher repeat_score.
        """
        c_a = CustomUser.objects.create(telegram_id=9001)
        c_b = CustomUser.objects.create(telegram_id=9002)

        # Scenario A: single purchase, 5 units
        self._create_txn(self.kefir, 5, customer=c_a)
        # Scenario B: five separate purchases, 1 unit each
        for _ in range(5):
            self._create_txn(self.kefir, 1, customer=c_b)

        calculate_personal_rankings(c_a.id)
        calculate_personal_rankings(c_b.id)

        score_a = ProductRanking.objects.get(
            customer=c_a, product=self.kefir,
        ).score
        score_b = ProductRanking.objects.get(
            customer=c_b, product=self.kefir,
        ).score

        # Both have same total qty (5), same category_score
        # But B has 5 purchase events vs A's 1 → higher repeat_score → higher final
        self.assertGreater(score_b, score_a)

        # Verify exact values
        # category score is 1000.0 for both (all qty is dairy)
        rep_a = (1 - math.exp(-REPEAT_DECAY * 1)) * 1000   # 1 event
        rep_b = (1 - math.exp(-REPEAT_DECAY * 5)) * 1000   # 5 events
        self.assertAlmostEqual(rep_a, 393.5, places=0)
        self.assertAlmostEqual(rep_b, 917.9, places=0)

    def test_recalculation_replaces_old_records(self):
        """Second calculation replaces previous records."""
        self._create_txn(self.kefir, 5)
        calculate_personal_rankings(self.customer.id)
        count_1 = ProductRanking.objects.filter(customer=self.customer).count()

        # Recalculate
        calculate_personal_rankings(self.customer.id)
        count_2 = ProductRanking.objects.filter(customer=self.customer).count()

        self.assertEqual(count_1, count_2)

    def test_score_stores_final_blended_score(self):
        """ProductRanking.score stores final_score, not personal_score."""
        self._create_txn(self.kefir, 10)

        calculate_personal_rankings(self.customer.id)

        record = ProductRanking.objects.get(
            customer=self.customer, product=self.kefir,
        )
        # final_score includes global_weight component, so must be different
        # from pure personal_score
        global_score = 800.0  # from setUp
        # times_bought = 1 (one txn with qty=10, repeat counts events)
        rep = (1 - math.exp(-REPEAT_DECAY * 1)) * 1000
        cat = 1000.0  # only dairy category
        personal = cat * CATEGORY_WEIGHT + rep * REPEAT_WEIGHT
        final = personal * PERSONAL_WEIGHT + global_score * GLOBAL_WEIGHT
        self.assertAlmostEqual(record.score, final, places=1)
        # Sanity: final != personal (unless GLOBAL_WEIGHT is 0)
        self.assertNotAlmostEqual(record.score, personal, places=1)


class CalculateAllPersonalRankingsTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.recent = self.now.date() - timedelta(days=10)

        root = Category.objects.create(name="Root", parent=None)
        self.dairy = Category.objects.create(name="Dairy", parent=root)

        self.product = Product.objects.create(
            name="Milk", price=Decimal("60"), category=self.dairy,
            is_active=True, store_id=1,
        )
        ProductRanking.objects.create(
            customer=None, product=self.product, score=500.0,
            calculated_at=self.now,
        )

    def test_multiple_customers(self):
        """Processes multiple customers correctly."""
        c1 = CustomUser.objects.create(telegram_id=2001)
        c2 = CustomUser.objects.create(telegram_id=2002)

        for c in (c1, c2):
            Transaction.objects.create(
                customer=c, product=self.product, quantity=3,
                total_amount=Decimal("180"), purchase_date=self.recent,
                store_id=1,
            )

        stats = calculate_all_personal_rankings()

        self.assertEqual(stats["customers_processed"], 2)
        self.assertGreater(stats["total_created"], 0)
        self.assertEqual(
            ProductRanking.objects.filter(customer=c1).count(), 1,
        )
        self.assertEqual(
            ProductRanking.objects.filter(customer=c2).count(), 1,
        )

    def test_stale_customer_cleanup(self):
        """Customers no longer in window get personal records removed."""
        c = CustomUser.objects.create(telegram_id=3001)
        # Create stale personal record (no transactions in window)
        ProductRanking.objects.create(
            customer=c, product=self.product, score=100.0,
            calculated_at=self.now,
        )

        stats = calculate_all_personal_rankings()

        self.assertGreater(stats["stale_deleted"], 0)
        self.assertEqual(
            ProductRanking.objects.filter(customer=c).count(), 0,
        )
