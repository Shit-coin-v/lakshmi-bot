from decimal import Decimal
from typing import Any

from rest_framework import serializers


class PurchaseSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
    product_code = serializers.CharField(max_length=50)
    product_name = serializers.CharField(max_length=200)
    category = serializers.CharField(max_length=100)
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"))
    total = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"))
    purchase_date = serializers.DateField(format="%d-%m-%Y")
    purchase_time = serializers.TimeField(format="%H:%M:%S")
    store_id = serializers.IntegerField()
    is_promotional = serializers.BooleanField()
    bonus_earned = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0")
    )
    total_bonuses = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=True, min_value=Decimal("0")
    )


class ReceiptPositionSerializer(serializers.Serializer):
    """Single receipt line accepted from 1C."""

    product_code = serializers.CharField()
    name = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    discount_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default=Decimal("0")
    )
    is_promotional = serializers.BooleanField(required=False, default=False)
    line_number = serializers.IntegerField(min_value=1)
    bonus_earned = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0")
    )
    category = serializers.CharField(required=False, allow_blank=True)


class ReceiptTotalsSerializer(serializers.Serializer):
    total_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0")
    )
    discount_total = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0")
    )
    bonus_spent = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0")
    )
    bonus_earned = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0")
    )


class ReceiptCustomerSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField(required=False, min_value=1)
    one_c_guid = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        return data


class ReceiptSerializer(serializers.Serializer):
    """Minimal schema for `/onec/receipt` payloads.

    Required fields (with types):

    * `receipt_guid` — string, unique receipt identifier.
    * `datetime` — ISO-8601 datetime of purchase.
    * `store_id` — store identifier (string or number).
    * `positions` — non-empty list of receipt lines. Each item must contain:
        - `line_number` (integer >= 1, unique per receipt),
        - `product_code` (string),
        - `quantity` (decimal > 0),
        - `price` (decimal >= 0).
      Optional item fields: `name`, `category`, `discount_amount`, `is_promotional`.
    * `totals` — object with `total_amount`, `discount_total`, `bonus_spent`,
      `bonus_earned` (all decimals >= 0).

    Optional fields:

    * `customer` — object with optional `telegram_id` (int) and/or `one_c_guid`
      (string). May be omitted entirely to process a guest receipt.
    """

    receipt_guid = serializers.CharField()
    datetime = serializers.DateTimeField()
    store_id = serializers.CharField()
    customer = ReceiptCustomerSerializer(required=False, allow_null=True)
    positions = ReceiptPositionSerializer(many=True, min_length=1)
    totals = ReceiptTotalsSerializer()

    def validate_customer(self, value: dict[str, Any] | None) -> dict[str, Any]:
        return value or {}

    def validate_positions(self, value):
        seen: set[int] = set()
        for position in value:
            line_number = position.get("line_number")
            if line_number in seen:
                raise serializers.ValidationError(
                    {"line_numbers": [line_number]},
                    code="duplicate_receipt_line",
                )
            seen.add(line_number)
        return value


class ProductUpdateSerializer(serializers.Serializer):
    product_code = serializers.CharField()
    one_c_guid = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    category = serializers.CharField()
    is_promotional = serializers.BooleanField()
    updated_at = serializers.DateTimeField()
