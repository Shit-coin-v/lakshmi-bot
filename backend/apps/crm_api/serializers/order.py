from rest_framework import serializers

from apps.orders.models import Order


class OrderListSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source="created_at")
    clientId = serializers.SerializerMethodField()
    clientName = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    purchaseType = serializers.CharField(source="fulfillment_type")
    items = serializers.SerializerMethodField()
    payment = serializers.CharField(source="payment_method")
    courier = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "date", "clientId", "clientName", "amount",
            "status", "purchaseType", "items", "address", "payment", "courier",
        ]

    def get_id(self, obj) -> str:
        return f"ORD-{obj.id}"

    def get_clientId(self, obj):
        return obj.customer.card_id if obj.customer_id else None

    def get_clientName(self, obj):
        return (obj.customer.full_name if obj.customer_id else "") or ""

    def get_amount(self, obj) -> int:
        return int(obj.total_price or 0)

    def get_items(self, obj) -> int:
        # _prefetched_items_count берётся из annotate в ListView; 0 — допустимое значение
        val = getattr(obj, "_prefetched_items_count", None)
        if val is None:
            return obj.items.count()
        return val

    def get_courier(self, obj) -> str:
        return str(obj.delivered_by) if obj.delivered_by else "—"
