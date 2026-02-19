from rest_framework import serializers

from apps.main.models import (
    BotActivity,
    CustomUser,
)
from apps.notifications.models import CourierNotificationMessage, PickerNotificationMessage
from apps.orders.models import Order, OrderItem


# --- Customer Bot serializers ---


class BotUserSerializer(serializers.ModelSerializer):
    """Read-only user representation for bots."""

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "telegram_id",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "email",
            "birth_date",
            "registration_date",
            "qr_code",
            "bonuses",
            "referrer_id",
            "last_purchase_date",
            "total_spent",
            "purchase_count",
            "personal_data_consent",
            "newsletter_enabled",
            "promo_enabled",
            "news_enabled",
            "general_enabled",
            "created_at",
            "password_hash",
            "email_verified",
            "auth_method",
        ]
        read_only_fields = fields


class UserRegisterSerializer(serializers.ModelSerializer):
    """Create a new user via Telegram registration."""

    referrer_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = CustomUser
        fields = [
            "telegram_id",
            "first_name",
            "last_name",
            "full_name",
            "birth_date",
            "qr_code",
            "referrer_id",
            "personal_data_consent",
        ]

    def validate_telegram_id(self, value):
        if CustomUser.objects.filter(telegram_id=value).exists():
            raise serializers.ValidationError("User with this telegram_id already exists.")
        return value

    def create(self, validated_data):
        referrer_id = validated_data.pop("referrer_id", None)
        if referrer_id is not None:
            try:
                referrer = CustomUser.objects.get(telegram_id=referrer_id)
                validated_data["referrer"] = referrer
            except CustomUser.DoesNotExist:
                pass  # ignore invalid referrer
        validated_data["auth_method"] = "telegram"
        return CustomUser.objects.create(**validated_data)


class UserPatchSerializer(serializers.ModelSerializer):
    """Partial update for bot-managed fields."""

    class Meta:
        model = CustomUser
        fields = ["qr_code", "bonuses"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False


class BotActivityCreateSerializer(serializers.Serializer):
    """Create a BotActivity record by telegram_id."""

    telegram_id = serializers.IntegerField()
    action = serializers.CharField(max_length=255)

    def create(self, validated_data):
        telegram_id = validated_data["telegram_id"]
        try:
            user = CustomUser.objects.get(telegram_id=telegram_id)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"telegram_id": "User not found."})
        return BotActivity.objects.create(
            customer=user,
            action=validated_data["action"],
        )


class NewsletterOpenSerializer(serializers.Serializer):
    """Register a newsletter open event."""

    token = serializers.CharField(max_length=64)
    telegram_user_id = serializers.IntegerField()
    raw_callback_data = serializers.CharField(max_length=128, required=False, default="")


class NewsletterOpenResponseSerializer(serializers.Serializer):
    """Response for newsletter open."""

    delivery_id = serializers.IntegerField()
    newly_opened = serializers.BooleanField()
    message_text = serializers.CharField()


class OneCMapUpsertSerializer(serializers.Serializer):
    """Upsert OneCClientMap."""

    user_id = serializers.IntegerField()
    one_c_guid = serializers.CharField(max_length=64)


# --- Courier Bot serializers ---


class ActiveOrderSerializer(serializers.ModelSerializer):
    """Lightweight order for the active orders list."""

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "created_at",
            "address",
            "phone",
            "comment",
            "customer_id",
            "products_price",
            "delivery_price",
            "total_price",
            "payment_method",
            "fulfillment_type",
        ]
        read_only_fields = fields


class OrderItemDetailSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", default="")
    product_id = serializers.IntegerField(source="product.id", default=None)

    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "product_name", "quantity", "price_at_moment"]
        read_only_fields = fields


class BotOrderDetailSerializer(serializers.ModelSerializer):
    """Full order detail with items for courier/picker bot."""

    items = OrderItemDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "created_at",
            "address",
            "phone",
            "comment",
            "customer_id",
            "products_price",
            "delivery_price",
            "total_price",
            "payment_method",
            "fulfillment_type",
            "assembled_by",
            "delivered_by",
            "completed_at",
            "items",
        ]
        read_only_fields = fields


class CourierMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourierNotificationMessage
        fields = ["id", "courier_tg_id", "telegram_message_id", "created_at"]
        read_only_fields = fields


class CourierMessageBulkDeleteSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


# --- Picker Bot serializers ---


class PickerMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickerNotificationMessage
        fields = ["id", "picker_tg_id", "telegram_message_id", "created_at"]
        read_only_fields = fields


class PickerMessageBulkDeleteSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


# --- Courier Profile serializers ---


class CourierProfileSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField(read_only=True)
    accepting_orders = serializers.BooleanField(read_only=True)


class CourierToggleAcceptingSerializer(serializers.Serializer):
    courier_tg_id = serializers.IntegerField()
    accepting = serializers.BooleanField()


# --- Staff registration serializers ---


class StaffRegisterSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
    full_name = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=20)
    role = serializers.ChoiceField(choices=["courier", "picker"])
