"""Tests for courier_assignment.py — round-robin courier assignment."""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.main.models import CustomUser, Product
from apps.orders.models import (
    CourierProfile,
    Order,
    OrderItem,
    RoundRobinCursor,
)
from apps.orders.courier_assignment import (
    _get_store_id,
    _pick_next,
    _get_available_couriers,
    assign_courier_to_order,
    get_unassigned_ready_orders,
    MAX_READY_ORDERS,
)


_TEST_SETTINGS = {
    "CACHES": {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
}


class PickNextTests(TestCase):
    """Pure logic tests for _pick_next round-robin."""

    def test_single_courier(self):
        self.assertEqual(_pick_next([100], None), 100)

    def test_first_assignment(self):
        self.assertEqual(_pick_next([100, 200, 300], None), 100)

    def test_round_robin_next(self):
        self.assertEqual(_pick_next([100, 200, 300], 100), 200)

    def test_round_robin_wrap(self):
        self.assertEqual(_pick_next([100, 200, 300], 300), 100)

    def test_round_robin_middle(self):
        self.assertEqual(_pick_next([100, 200, 300], 200), 300)

    def test_last_was_removed_skips_to_next(self):
        # last_tg_id=150 is not in the list, next > 150 is 200
        self.assertEqual(_pick_next([100, 200, 300], 150), 200)

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            _pick_next([], None)


@override_settings(**_TEST_SETTINGS)
class GetAvailableCouriersTests(TestCase):
    def test_no_couriers(self):
        self.assertEqual(_get_available_couriers(), [])

    def test_approved_accepting_courier(self):
        CourierProfile.objects.create(
            telegram_id=1001, is_approved=True, is_blacklisted=False, accepting_orders=True,
        )
        self.assertEqual(_get_available_couriers(), [1001])

    def test_unapproved_excluded(self):
        CourierProfile.objects.create(
            telegram_id=1002, is_approved=False, accepting_orders=True,
        )
        self.assertEqual(_get_available_couriers(), [])

    def test_blacklisted_excluded(self):
        CourierProfile.objects.create(
            telegram_id=1003, is_approved=True, is_blacklisted=True, accepting_orders=True,
        )
        self.assertEqual(_get_available_couriers(), [])

    def test_not_accepting_excluded(self):
        CourierProfile.objects.create(
            telegram_id=1004, is_approved=True, accepting_orders=False,
        )
        self.assertEqual(_get_available_couriers(), [])

    def test_on_route_excluded(self):
        CourierProfile.objects.create(
            telegram_id=1005, is_approved=True, accepting_orders=True,
        )
        customer = CustomUser.objects.create(telegram_id=50001)
        Order.objects.create(
            customer=customer, address="t", phone="+7",
            total_price=100, products_price=100,
            status="delivery", delivered_by=1005,
        )
        self.assertEqual(_get_available_couriers(), [])

    def test_arrived_status_excluded(self):
        CourierProfile.objects.create(
            telegram_id=1006, is_approved=True, accepting_orders=True,
        )
        customer = CustomUser.objects.create(telegram_id=50002)
        Order.objects.create(
            customer=customer, address="t", phone="+7",
            total_price=100, products_price=100,
            status="arrived", delivered_by=1006,
        )
        self.assertEqual(_get_available_couriers(), [])

    def test_overloaded_courier_excluded(self):
        CourierProfile.objects.create(
            telegram_id=1007, is_approved=True, accepting_orders=True,
        )
        customer = CustomUser.objects.create(telegram_id=50003)
        for _ in range(MAX_READY_ORDERS):
            Order.objects.create(
                customer=customer, address="t", phone="+7",
                total_price=100, products_price=100,
                status="ready", delivered_by=1007,
            )
        self.assertEqual(_get_available_couriers(), [])

    def test_below_max_ready_included(self):
        CourierProfile.objects.create(
            telegram_id=1008, is_approved=True, accepting_orders=True,
        )
        customer = CustomUser.objects.create(telegram_id=50004)
        for _ in range(MAX_READY_ORDERS - 1):
            Order.objects.create(
                customer=customer, address="t", phone="+7",
                total_price=100, products_price=100,
                status="ready", delivered_by=1008,
            )
        self.assertEqual(_get_available_couriers(), [1008])

    def test_multiple_couriers_sorted(self):
        for tg_id in [1020, 1010, 1030]:
            CourierProfile.objects.create(
                telegram_id=tg_id, is_approved=True, accepting_orders=True,
            )
        self.assertEqual(_get_available_couriers(), [1010, 1020, 1030])


@override_settings(**_TEST_SETTINGS)
class AssignCourierToOrderTests(TestCase):
    def setUp(self):
        self.customer = CustomUser.objects.create(telegram_id=50010)
        self.product = Product.objects.create(
            product_code="CA-1", name="Test", price="100.00", store_id=1, is_active=True,
        )

    def _make_order(self, status="ready", fulfillment_type="delivery", delivered_by=None):
        order = Order.objects.create(
            customer=self.customer, address="addr", phone="+7",
            total_price=100, products_price=100,
            status=status, fulfillment_type=fulfillment_type,
            delivered_by=delivered_by,
        )
        OrderItem.objects.create(
            order=order, product=self.product,
            quantity=1, price_at_moment=Decimal("100.00"),
        )
        return order

    def test_assigns_to_available_courier(self):
        CourierProfile.objects.create(
            telegram_id=2001, is_approved=True, accepting_orders=True,
        )
        order = self._make_order()

        result = assign_courier_to_order(order.id)
        self.assertEqual(result, 2001)

        order.refresh_from_db()
        self.assertEqual(order.delivered_by, 2001)

    def test_updates_cursor(self):
        CourierProfile.objects.create(
            telegram_id=2002, is_approved=True, accepting_orders=True,
        )
        order = self._make_order()
        assign_courier_to_order(order.id)

        cursor = RoundRobinCursor.objects.get(store_id=1)
        self.assertEqual(cursor.last_courier_tg_id, 2002)

    def test_round_robin_across_orders(self):
        for tg_id in [2010, 2020, 2030]:
            CourierProfile.objects.create(
                telegram_id=tg_id, is_approved=True, accepting_orders=True,
            )

        order1 = self._make_order()
        order2 = self._make_order()
        order3 = self._make_order()

        r1 = assign_courier_to_order(order1.id)
        r2 = assign_courier_to_order(order2.id)
        r3 = assign_courier_to_order(order3.id)

        self.assertEqual(r1, 2010)
        self.assertEqual(r2, 2020)
        self.assertEqual(r3, 2030)

    def test_no_available_couriers(self):
        order = self._make_order()
        result = assign_courier_to_order(order.id)
        self.assertIsNone(result)

    def test_order_not_found(self):
        result = assign_courier_to_order(999999)
        self.assertIsNone(result)

    def test_skip_non_ready_order(self):
        CourierProfile.objects.create(
            telegram_id=2040, is_approved=True, accepting_orders=True,
        )
        order = self._make_order(status="new")
        result = assign_courier_to_order(order.id)
        self.assertIsNone(result)

    def test_skip_pickup_order(self):
        CourierProfile.objects.create(
            telegram_id=2050, is_approved=True, accepting_orders=True,
        )
        order = self._make_order(fulfillment_type="pickup")
        result = assign_courier_to_order(order.id)
        self.assertIsNone(result)

    def test_skip_already_assigned(self):
        CourierProfile.objects.create(
            telegram_id=2060, is_approved=True, accepting_orders=True,
        )
        order = self._make_order(delivered_by=9999)
        result = assign_courier_to_order(order.id)
        self.assertIsNone(result)

    def test_wrap_around_round_robin(self):
        """When cursor points to last courier, should wrap to first."""
        for tg_id in [3001, 3002, 3003]:
            CourierProfile.objects.create(
                telegram_id=tg_id, is_approved=True, accepting_orders=True,
            )
        # Pre-set cursor to last
        RoundRobinCursor.objects.create(store_id=1, last_courier_tg_id=3003)

        order = self._make_order()
        result = assign_courier_to_order(order.id)
        self.assertEqual(result, 3001)


@override_settings(**_TEST_SETTINGS)
class GetUnassignedReadyOrdersTests(TestCase):
    def setUp(self):
        self.customer = CustomUser.objects.create(telegram_id=50020)

    def test_returns_matching_orders(self):
        order = Order.objects.create(
            customer=self.customer, address="t", phone="+7",
            total_price=100, products_price=100,
            status="ready", fulfillment_type="delivery",
        )
        result = get_unassigned_ready_orders()
        self.assertIn(order.id, result)

    def test_excludes_assigned(self):
        Order.objects.create(
            customer=self.customer, address="t", phone="+7",
            total_price=100, products_price=100,
            status="ready", fulfillment_type="delivery",
            delivered_by=1234,
        )
        result = get_unassigned_ready_orders()
        self.assertEqual(result, [])

    def test_excludes_non_ready(self):
        Order.objects.create(
            customer=self.customer, address="t", phone="+7",
            total_price=100, products_price=100,
            status="new", fulfillment_type="delivery",
        )
        result = get_unassigned_ready_orders()
        self.assertEqual(result, [])

    def test_excludes_pickup(self):
        Order.objects.create(
            customer=self.customer, address="t", phone="+7",
            total_price=100, products_price=100,
            status="ready", fulfillment_type="pickup",
        )
        result = get_unassigned_ready_orders()
        self.assertEqual(result, [])


@override_settings(**_TEST_SETTINGS)
class GetStoreIdTests(TestCase):
    def test_extracts_from_first_item(self):
        customer = CustomUser.objects.create(telegram_id=50030)
        product = Product.objects.create(
            product_code="SI-1", name="T", price="10.00", store_id=5, is_active=True,
        )
        order = Order.objects.create(
            customer=customer, address="t", phone="+7",
            total_price=10, products_price=10,
        )
        OrderItem.objects.create(
            order=order, product=product, quantity=1, price_at_moment=Decimal("10.00"),
        )
        self.assertEqual(_get_store_id(order), 5)

    def test_no_items_returns_zero(self):
        customer = CustomUser.objects.create(telegram_id=50031)
        order = Order.objects.create(
            customer=customer, address="t", phone="+7",
            total_price=10, products_price=10,
        )
        self.assertEqual(_get_store_id(order), 0)
