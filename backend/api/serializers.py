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

