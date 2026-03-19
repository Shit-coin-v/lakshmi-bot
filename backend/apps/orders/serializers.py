import logging
from decimal import Decimal

from rest_framework import serializers

from apps.common.models import SiteSettings
from apps.main.models import Category
from apps.orders.models import Order, OrderItem, Product

from apps.orders.services import get_delivery_price

logger = logging.getLogger(__name__)


class CategoryListSerializer(serializers.ModelSerializer):
    has_children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'parent_id', 'has_children']

    def get_has_children(self, obj):
        return obj.children.filter(is_active=True).exists()


class ProductListSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    category = serializers.CharField(source='category_text', read_only=True)
    stock = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'product_code',
            'name',
            'price',
            'category',
            'stock', 
            'image_url',     
            'description',   
            'is_promotional'
        ]

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None


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
    courier_phone = serializers.SerializerMethodField()
    picker_phone = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "created_at",
            "status",
            "status_display",
            "payment_method",
            "payment_status",
            "fulfillment_type",
            "address",
            "phone",
            "comment",
            "products_price",
            "delivery_price",
            "total_price",
            "items",
            "courier_phone",
            "picker_phone",
        ]

    def _get_staff_phones(self):
        """Cache staff phone lookup per serializer instance to avoid N+1."""
        if not hasattr(self, "_staff_phone_cache"):
            from apps.orders.models import CourierProfile, PickerProfile
            self._staff_phone_cache = {
                "couriers": dict(
                    CourierProfile.objects.filter(phone__gt="")
                    .values_list("telegram_id", "phone")
                ),
                "pickers": dict(
                    PickerProfile.objects.filter(phone__gt="")
                    .values_list("telegram_id", "phone")
                ),
            }
        return self._staff_phone_cache

    def get_courier_phone(self, obj):
        if not obj.delivered_by:
            return None
        return self._get_staff_phones()["couriers"].get(obj.delivered_by)

    def get_picker_phone(self, obj):
        if not obj.assembled_by:
            return None
        return self._get_staff_phones()["pickers"].get(obj.assembled_by)


class OrderListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'created_at',
            'total_price',
            'status',
            'status_display',
            'fulfillment_type',
            'items_count',
        ]


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
        read_only_fields = ["customer"]

    def to_internal_value(self, data):
        if isinstance(data, dict) and "customer" not in data and "customer_id" in data:
            data = {**data, "customer": data.get("customer_id")}

        if isinstance(data, dict):
            ft = (data.get("fulfillment_type") or "").strip()
            addr = (data.get("address") or "").strip()

            # If frontend omits fulfillment_type but address is "Самовывоз",
            # treat as pickup (skip delivery fee).
            if not ft and addr.casefold() == "самовывоз":
                data = {**data, "fulfillment_type": "pickup"}
                ft = "pickup"

            if ft == "pickup" and not addr:
                data = {**data, "address": "Самовывоз"}

        return super().to_internal_value(data)

    def validate(self, attrs):
        ft = attrs.get("fulfillment_type") or "delivery"
        settings = SiteSettings.load()

        if ft == "delivery" and not settings.delivery_enabled:
            msg = settings.delivery_disabled_message or "Доставка временно недоступна"
            raise serializers.ValidationError({"fulfillment_type": msg})

        if ft == "pickup" and not settings.pickup_enabled:
            msg = settings.pickup_disabled_message or "Самовывоз временно недоступен"
            raise serializers.ValidationError({"fulfillment_type": msg})

        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        validated_data.pop("total_price", None)

        fulfillment_type = validated_data.get("fulfillment_type") or "delivery"
        delivery_price = Decimal("0.00") if fulfillment_type == "pickup" else get_delivery_price()
        is_sbp = validated_data.get("payment_method") == "sbp"

        order = Order.objects.create(
            products_price=Decimal("0.00"),
            delivery_price=delivery_price,
            total_price=Decimal("0.00"),
            payment_status="pending" if is_sbp else "none",
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

        if is_sbp:
            # Create ЮKassa payment (hold)
            from apps.integrations.payments.yukassa_client import create_payment

            try:
                result = create_payment(
                    amount=order.total_price,
                    order_id=order.id,
                )
                order.payment_id = result["payment_id"]
                order.save(update_fields=["products_price", "total_price", "payment_id"])
                # Store confirmation_url for the view to return
                order._confirmation_url = result["confirmation_url"]
            except Exception:
                logger.exception("Failed to create YooKassa payment for order %s", order.id)
                order.payment_status = "failed"
                order.status = "canceled"
                order._skip_signal_notification = True
                order.save(update_fields=["products_price", "total_price", "payment_status", "status"])
                raise serializers.ValidationError({"payment": "Не удалось создать платёж. Попробуйте позже."})
        else:
            order.save(update_fields=["products_price", "total_price"])
            # Non-SBP: send to 1C and notify immediately
            from apps.integrations.onec.tasks import send_order_to_onec
            send_order_to_onec.delay(order.id)

        return order
