from decimal import Decimal
from typing import Any

from rest_framework import serializers


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
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
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


class OneCCategoryItemSerializer(serializers.Serializer):
    external_id = serializers.CharField()
    name = serializers.CharField()
    parent_external_id = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=None,
    )
    is_active = serializers.BooleanField(required=False, default=True)
    sort_order = serializers.IntegerField(required=False, default=0)


class OneCCategorySyncSerializer(serializers.Serializer):
    categories = OneCCategoryItemSerializer(many=True, min_length=1)


class StockItemSerializer(serializers.Serializer):
    product_code = serializers.CharField()
    stock = serializers.IntegerField(min_value=0)


class StockUpdateSerializer(serializers.Serializer):
    items = StockItemSerializer(many=True, min_length=1)
