from decimal import Decimal
from rest_framework import serializers


class PurchaseSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
    product_code = serializers.CharField(max_length=50)
    product_name = serializers.CharField(max_length=200)
    category = serializers.CharField(max_length=100)
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'))
    total = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'))
    purchase_date = serializers.DateField(format='%d-%m-%Y')
    purchase_time = serializers.TimeField(format='%H:%M:%S')
    store_id = serializers.IntegerField()
    is_promotional = serializers.BooleanField()
    bonus_earned = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'))
    total_bonuses = serializers.DecimalField(max_digits=10, decimal_places=2, required=True, min_value=Decimal('0'))


class ReceiptPositionSerializer(serializers.Serializer):
    product_code = serializers.CharField()
    name = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    is_promotional = serializers.BooleanField()
    line_number = serializers.IntegerField()


class ReceiptTotalsSerializer(serializers.Serializer):
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    discount_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    bonus_spent = serializers.DecimalField(max_digits=14, decimal_places=2)
    bonus_earned = serializers.DecimalField(max_digits=14, decimal_places=2)


class ReceiptCustomerSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField(required=False)
    one_c_guid = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if not data.get('telegram_id') and not data.get('one_c_guid'):
            raise serializers.ValidationError("telegram_id или one_c_guid обязателен")
        return data


class ReceiptSerializer(serializers.Serializer):
    receipt_guid = serializers.CharField()
    datetime = serializers.DateTimeField()  # ISO 8601
    store_id = serializers.CharField()     # строка/число — оставим строкой
    customer = ReceiptCustomerSerializer()
    positions = ReceiptPositionSerializer(many=True)
    totals = ReceiptTotalsSerializer()


class ProductUpdateSerializer(serializers.Serializer):
    product_code = serializers.CharField()
    one_c_guid = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    category = serializers.CharField()
    is_promotional = serializers.BooleanField()
    updated_at = serializers.DateTimeField()
