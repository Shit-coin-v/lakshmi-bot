import logging
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.common.models import SiteSettings
from apps.main.models import Category
from apps.orders.models import Order, OrderItem, Product
from apps.orders.pricing import compute_payment_amount, compute_products_and_total

logger = logging.getLogger(__name__)


class CategoryListSerializer(serializers.ModelSerializer):
    has_children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'parent_id', 'has_children']

    def get_has_children(self, obj):
        qs = obj.children.filter(is_active=True)
        request = self.context.get("request") if self.context else None
        if request is not None:
            from apps.main.services.catalog_filters import request_can_view_hidden

            if not request_can_view_hidden(request):
                qs = qs.exclude(hide_from_app=True)
        else:
            # Без request не можем проверить staff-права — по умолчанию скрываем.
            qs = qs.exclude(hide_from_app=True)
        return qs.exists()


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
    payment_amount = serializers.SerializerMethodField()

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
            "bonus_used",
            "payment_amount",
            "delivery_zone_code",
            "items",
            "courier_phone",
            "picker_phone",
        ]

    def get_payment_amount(self, obj):
        return str(compute_payment_amount(obj.total_price, obj.bonus_used))

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
    items = OrderItemSerializer(many=True, min_length=1)
    delivery_zone_code = serializers.CharField(required=False, allow_blank=True, default="")
    bonus_used = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=Decimal("0.00"),
        min_value=Decimal("0"),
    )

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
            "delivery_zone_code",
            "total_price",
            "bonus_used",
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

        zone_code = (attrs.get("delivery_zone_code") or "").strip()

        if ft == "delivery":
            if not zone_code:
                raise serializers.ValidationError({"delivery_zone_code": "Выберите зону доставки."})

            from apps.orders.models import DeliveryZone
            zone = DeliveryZone.objects.filter(product_code=zone_code, is_active=True).first()
            if not zone:
                raise serializers.ValidationError({"delivery_zone_code": "Зона доставки недоступна."})

            from apps.main.models import Product as ProductModel
            product = ProductModel.objects.filter(
                product_code=zone_code, is_active=True, price__isnull=False,
            ).first()
            if not product:
                raise serializers.ValidationError({"delivery_zone_code": "Стоимость доставки недоступна."})

            attrs["_delivery_price"] = product.price
            attrs["delivery_zone_code"] = zone_code
        else:
            attrs["delivery_zone_code"] = None
            attrs["_delivery_price"] = Decimal("0.00")

        # --- Compute server-side prices (source of truth) ---
        items_data = attrs.get("items", [])
        delivery_price = attrs["_delivery_price"]
        server_products, server_total = compute_products_and_total(items_data, delivery_price)
        attrs["_server_products_price"] = server_products
        attrs["_server_total_price"] = server_total

        # --- bonus_used validation ---
        bonus_used = attrs.get("bonus_used") or Decimal("0.00")
        if bonus_used > 0:
            max_bonus = (server_total / 2).quantize(Decimal("0.01"))

            if bonus_used > max_bonus:
                raise serializers.ValidationError({
                    "bonus_used": f"Максимум можно списать {max_bonus} бонусов (50% от суммы заказа)."
                })

            request = self.context.get("request")
            customer = getattr(request, "telegram_user", None) if request else None
            if customer:
                available = customer.bonuses or Decimal("0.00")
                if bonus_used > available:
                    raise serializers.ValidationError({
                        "bonus_used": f"Недостаточно бонусов. Доступно: {available}."
                    })

            if compute_payment_amount(server_total, bonus_used) < 0:
                raise serializers.ValidationError({
                    "bonus_used": "Сумма списания превышает сумму заказа."
                })

        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        validated_data.pop("total_price", None)
        delivery_price = validated_data.pop("_delivery_price")
        bonus_used = validated_data.pop("bonus_used", Decimal("0.00")) or Decimal("0.00")
        server_products = validated_data.pop("_server_products_price")
        server_total = validated_data.pop("_server_total_price")
        is_sbp = validated_data.get("payment_method") == "sbp"

        # Фаза 1: создание Order + OrderItem в одной БД-транзакции.
        # Сетевой вызов ЮKassa вынесен наружу, чтобы не держать БД-транзакцию
        # открытой во время HTTP I/O.
        with transaction.atomic():
            order = Order.objects.create(
                products_price=server_products,
                delivery_price=delivery_price,
                total_price=server_total,
                bonus_used=bonus_used,
                payment_status="pending" if is_sbp else "none",
                **validated_data,
            )

            for item in items_data:
                OrderItem.objects.create(
                    order=order,
                    product=item["product"],
                    quantity=int(item["quantity"]),
                    price_at_moment=item["product"].price,
                )

            if not is_sbp:
                # Не-СБП: отправка в 1С после коммита транзакции,
                # чтобы Celery-task точно увидел заказ в БД.
                from apps.integrations.onec.tasks import send_order_to_onec
                oid = order.id
                transaction.on_commit(lambda: send_order_to_onec.delay(oid))

        if not is_sbp:
            return order

        # Фаза 2: внешний HTTP-вызов ЮKassa без БД-транзакции.
        # Импортируем поздно, чтобы не тянуть SDK ЮKassa при загрузке Django.
        from asyncio import TimeoutError as asyncio_TimeoutError

        from requests.exceptions import RequestException

        from apps.integrations.payments.yukassa_client import (
            YukassaLogicalError,
            create_payment,
        )

        try:
            result = create_payment(
                amount=order.total_price,
                order_id=order.id,
            )
        except YukassaLogicalError as exc:
            # 4xx — терминально, ретраи не помогут, помечаем заказ как failed/canceled.
            logger.error(
                "YooKassa logical error creating payment for order %s: %s",
                order.id, exc,
            )
            with transaction.atomic():
                order.payment_status = "failed"
                order.status = "canceled"
                order._skip_signal_notification = True
                order.save(update_fields=["payment_status", "status"])
            raise serializers.ValidationError(
                {"payment": "Не удалось создать платёж. Попробуйте позже."}
            )
        except (RequestException, OSError, asyncio_TimeoutError) as exc:
            # Сетевая ошибка — отдельное user-friendly сообщение.
            logger.warning(
                "YooKassa network error creating payment for order %s: %s",
                order.id, exc,
            )
            with transaction.atomic():
                order.payment_status = "failed"
                order.status = "canceled"
                order._skip_signal_notification = True
                order.save(update_fields=["payment_status", "status"])
            raise serializers.ValidationError(
                {"payment": "Платёж недоступен, попробуйте позже."}
            )
        except Exception:
            # Неожиданная ошибка — full traceback в Sentry/логи.
            logger.exception(
                "Unexpected error creating YooKassa payment for order %s", order.id,
            )
            with transaction.atomic():
                order.payment_status = "failed"
                order.status = "canceled"
                order._skip_signal_notification = True
                order.save(update_fields=["payment_status", "status"])
            raise serializers.ValidationError(
                {"payment": "Не удалось создать платёж. Попробуйте позже."}
            )

        # Фаза 3: записать payment_id в отдельной транзакции.
        with transaction.atomic():
            order.payment_id = result["payment_id"]
            order.save(update_fields=["payment_id"])
        order._confirmation_url = result["confirmation_url"]

        return order
