"""Order pricing calculations — single source of truth.

Used by serializers, order_sync (1C payload), and tests.
"""

from decimal import Decimal


def compute_products_and_total(items_data, delivery_price):
    """Compute order prices from server-side product prices.

    Args:
        items_data: list of dicts, each must have "product" (Product instance)
                    and "quantity" (int-like).
        delivery_price: Decimal delivery cost.

    Returns:
        (products_price, total_price) — both Decimal, quantized to 0.01.
    """
    products_price = sum(
        (it["product"].price * int(it["quantity"]) for it in items_data),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"))
    total_price = (products_price + delivery_price).quantize(Decimal("0.01"))
    return products_price, total_price


def compute_payment_amount(total_price, bonus_used):
    """Compute amount the customer pays after bonus deduction.

    Args:
        total_price: Decimal total order price.
        bonus_used: Decimal or None — bonuses applied.

    Returns:
        Decimal payment amount, quantized to 0.01.
    """
    bonus = bonus_used or Decimal("0")
    return (total_price - bonus).quantize(Decimal("0.01"))


def format_money(value) -> str:
    """Format a monetary value as a string with exactly 2 decimal places.

    None and zero both become "0.00".
    """
    if value is None:
        return "0.00"
    return str(Decimal(str(value)).quantize(Decimal("0.01")))
