from rest_framework import serializers


class PurchaseSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
    product_code = serializers.CharField()
    product_name = serializers.CharField()
    category = serializers.CharField()
    quantity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = serializers.DateField()
    purchase_time = serializers.TimeField()
    store_id = serializers.IntegerField()
    is_promotional = serializers.BooleanField()
    bonus_earned = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_bonuses = serializers.DecimalField(max_digits=10, decimal_places=2, required=True, min_value=0)
