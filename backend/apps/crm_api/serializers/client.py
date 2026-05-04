from rest_framework import serializers

from apps.main.models import CustomUser
from apps.rfm.constants import SEGMENT_LABEL_RU


def _segment_label(user) -> str:
    profile = getattr(user, "rfm_profile", None)
    return (profile.segment_label if profile else "") or "—"


def _segment_label_ru(user) -> str:
    """Русское отображение RFM-сегмента. Если профиля нет → '—'."""
    code = _segment_label(user)
    if code == "—":
        return "—"
    return SEGMENT_LABEL_RU.get(code, code)


def _last_order_iso(user) -> str | None:
    if not user.last_purchase_date:
        return None
    return user.last_purchase_date.date().isoformat()


def _tags(user) -> list[str]:
    tags = []
    if (user.purchase_count or 0) >= 30:
        tags.append("vip")
    if (user.bonuses or 0) >= 1000:
        tags.append("много бонусов")
    if user.email and user.telegram_id:
        tags.append("мульти-канал")
    return tags


class ClientListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="card_id")
    name = serializers.CharField(source="full_name", default="")
    rfmSegment = serializers.SerializerMethodField()
    bonus = serializers.SerializerMethodField()
    ltv = serializers.SerializerMethodField()
    purchaseCount = serializers.IntegerField(source="purchase_count", default=0)
    lastOrder = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id", "name", "phone", "email",
            "rfmSegment", "bonus", "ltv", "purchaseCount", "lastOrder", "tags",
        ]

    def get_rfmSegment(self, obj) -> str:
        return _segment_label_ru(obj)

    def get_bonus(self, obj) -> int:
        return int(obj.bonuses or 0)

    def get_ltv(self, obj) -> int:
        return int(obj.total_spent or 0)

    def get_lastOrder(self, obj):
        return _last_order_iso(obj)

    def get_tags(self, obj) -> list[str]:
        return _tags(obj)


class _OrderInClientSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    date = serializers.DateTimeField(source="created_at")
    amount = serializers.SerializerMethodField()
    status = serializers.CharField()

    def get_id(self, obj) -> str:
        return f"ORD-{obj.id}"

    def get_amount(self, obj) -> int:
        return int(obj.total_price or 0)


class _CampaignInClientSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    name = serializers.CharField()
    rules = serializers.SerializerMethodField()

    def get_id(self, obj) -> str:
        return f"CMP-{obj.id}"

    def get_rules(self, obj) -> str:
        first = obj.rules.first() if hasattr(obj, "rules") else None
        if not first:
            return ""
        return f"{first.reward_type}: {first.reward_value or first.reward_percent or ''}".strip()


class ClientDetailSerializer(ClientListSerializer):
    telegramId = serializers.IntegerField(source="telegram_id", default=None)
    preferences = serializers.SerializerMethodField()
    orders = serializers.SerializerMethodField()
    activeCampaigns = serializers.SerializerMethodField()

    class Meta(ClientListSerializer.Meta):
        fields = ClientListSerializer.Meta.fields + ["telegramId", "preferences", "orders", "activeCampaigns"]

    def get_preferences(self, obj) -> dict:
        return {
            "push": bool(obj.general_enabled),
            "telegram": bool(obj.telegram_id),
            "email": bool(obj.promo_enabled),
            "sms": False,
        }

    def get_orders(self, obj) -> list[dict]:
        orders = obj.orders.order_by("-created_at")[:20]
        return _OrderInClientSerializer(orders, many=True).data

    def get_activeCampaigns(self, obj) -> list[dict]:
        """Активные кампании, чей RFM-сегмент совпадает с сегментом клиента."""
        from apps.campaigns.models import Campaign
        segment = _segment_label(obj)
        if segment == "—":
            return []
        qs = Campaign.objects.filter(is_active=True, rfm_segment=segment).prefetch_related("rules")[:10]
        return _CampaignInClientSerializer(qs, many=True).data
