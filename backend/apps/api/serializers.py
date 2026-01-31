from decimal import Decimal
from typing import Any

from rest_framework import serializers
from apps.main.models import Product, Order, OrderItem, CustomUser, Notification
from apps.orders.serializers import ProductListSerializer  # noqa: F401


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


class OrderItemSerializer(serializers.Serializer):
    product_code = serializers.CharField(required=False, allow_blank=False)
    product_id = serializers.CharField(required=False, allow_blank=False)
    quantity = serializers.IntegerField(min_value=1)
    price_at_moment = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )

    def validate(self, attrs):
        code = (attrs.get("product_code") or attrs.get("product_id") or "").strip()
        if not code:
            raise serializers.ValidationError({"product_code": ["Обязательное поле."]})

        try:
            product = Product.objects.get(product_code=code)
        except Product.DoesNotExist:
            raise serializers.ValidationError({"product_code": ["Товар не найден."]})

        attrs["product"] = product

        if attrs.get("price_at_moment") in (None, ""):
            attrs["price_at_moment"] = product.price

        return attrs


# backend/apps/api/serializers.py

class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "address",
            "phone",
            "comment",
            "payment_method",
            "fulfillment_type",
            "total_price",
            "items",
        ]

    def to_internal_value(self, data):
        if isinstance(data, dict) and "customer" not in data and "customer_id" in data:
            data = {**data, "customer": data.get("customer_id")}

        if isinstance(data, dict):
            ft = (data.get("fulfillment_type") or "").strip()
            addr = (data.get("address") or "").strip()

            # ✅ Если фронт не прислал fulfillment_type, но адрес = "Самовывоз",
            # считаем это самовывозом (чтобы не добавлялась доставка 150).
            if not ft and addr.casefold() == "самовывоз":
                data = {**data, "fulfillment_type": "pickup"}
                ft = "pickup"

            if ft == "pickup" and not addr:
                data = {**data, "address": "Самовывоз"}

        return super().to_internal_value(data)


    def create(self, validated_data):
        items_data = validated_data.pop("items")
        validated_data.pop("total_price", None)

        fulfillment_type = validated_data.get("fulfillment_type") or "delivery"
        delivery_price = Decimal("0.00") if fulfillment_type == "pickup" else Decimal("150.00")

        order = Order.objects.create(
            products_price=Decimal("0.00"),
            delivery_price=delivery_price,
            total_price=Decimal("0.00"),
            **validated_data,
        )


        products_sum = Decimal("0.00")

        for item in items_data:
            qty = int(item["quantity"])
            price = Decimal(item["price_at_moment"])
            products_sum += price * qty

            OrderItem.objects.create(
                order=order,
                product=item["product"],
                quantity=qty,
                price_at_moment=price,
            )

        order.products_price = products_sum.quantize(Decimal("0.01"))
        order.total_price = (order.products_price + (order.delivery_price or Decimal("0.00"))).quantize(
            Decimal("0.01")
        )
        order.save(update_fields=["products_price", "total_price"])

        from apps.integrations.onec.task_contract import send_order_to_onec

        send_order_to_onec(order.id)

        return order
    

class OrderListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items_count = serializers.IntegerField(source='items.count', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 
            'created_at', 
            'total_price', 
            'status', 
            'status_display', 
            'items_count'
        ]

class OrderItemDetailSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.product_code", read_only=True)
    name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "product_code",
            "name",
            "quantity",
            "price_at_moment",
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items = OrderItemDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "created_at",
            "status",
            "status_display",
            "payment_method",
            "fulfillment_type",
            "address",
            "phone",
            "comment",
            "products_price",
            "delivery_price",
            "total_price",
            "items",
        ]


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id', 
            'telegram_id', 
            'full_name', 
            'phone', 
            'email', 
            'bonuses', 
            'qr_code',
            'avatar'
        ]
        read_only_fields = ['id', 'telegram_id', 'bonuses', 'qr_code']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "user_id", "title", "body", "is_read", "created_at", "type")
        read_only_fields = fields


class NotificationReadSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    source = serializers.ChoiceField(choices=["inapp", "push"], required=False, default="inapp")


class UpdateFCMTokenSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(required=False)
    user_id = serializers.IntegerField(required=False)
    fcm_token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(choices=("android", "ios", "web"), required=False, default="android")

    def validate(self, attrs):
        customer_id = attrs.get("customer_id")
        user_id = attrs.get("user_id")

        if not customer_id and user_id:
            attrs["customer_id"] = user_id

        if not attrs.get("customer_id"):
            raise serializers.ValidationError({"customer_id": "Обязательное поле (или передай user_id)."})
        return attrs
