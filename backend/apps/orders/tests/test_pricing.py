"""Unit tests for apps.orders.pricing module."""

from decimal import Decimal
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.orders.pricing import (
    compute_payment_amount,
    compute_products_and_total,
    format_money,
)


class FormatMoneyTests(SimpleTestCase):
    def test_none(self):
        self.assertEqual(format_money(None), "0.00")

    def test_zero_int(self):
        self.assertEqual(format_money(0), "0.00")

    def test_zero_decimal(self):
        self.assertEqual(format_money(Decimal("0")), "0.00")

    def test_one_decimal_place(self):
        self.assertEqual(format_money(Decimal("12.3")), "12.30")

    def test_two_decimal_places(self):
        self.assertEqual(format_money(Decimal("99.99")), "99.99")

    def test_integer_value(self):
        self.assertEqual(format_money(1000), "1000.00")

    def test_string_numeric(self):
        self.assertEqual(format_money("50.5"), "50.50")


class ComputeProductsAndTotalTests(SimpleTestCase):
    def _make_item(self, price, quantity):
        product = MagicMock()
        product.price = Decimal(str(price))
        return {"product": product, "quantity": quantity}

    def test_empty_items(self):
        products, total = compute_products_and_total([], Decimal("100.00"))
        self.assertEqual(products, Decimal("0.00"))
        self.assertEqual(total, Decimal("100.00"))

    def test_single_item(self):
        items = [self._make_item(500, 2)]
        products, total = compute_products_and_total(items, Decimal("100.00"))
        self.assertEqual(products, Decimal("1000.00"))
        self.assertEqual(total, Decimal("1100.00"))

    def test_multiple_items(self):
        items = [self._make_item(100, 3), self._make_item(50, 2)]
        products, total = compute_products_and_total(items, Decimal("0.00"))
        self.assertEqual(products, Decimal("400.00"))
        self.assertEqual(total, Decimal("400.00"))


class ComputePaymentAmountTests(SimpleTestCase):
    def test_no_bonus(self):
        self.assertEqual(
            compute_payment_amount(Decimal("1000.00"), Decimal("0")),
            Decimal("1000.00"),
        )

    def test_none_bonus(self):
        self.assertEqual(
            compute_payment_amount(Decimal("1000.00"), None),
            Decimal("1000.00"),
        )

    def test_with_bonus(self):
        self.assertEqual(
            compute_payment_amount(Decimal("1000.00"), Decimal("300.00")),
            Decimal("700.00"),
        )
