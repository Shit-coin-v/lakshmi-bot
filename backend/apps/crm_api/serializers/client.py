from rest_framework import serializers

from apps.main.models import CustomUser


def _segment_label(user) -> str:
    profile = getattr(user, "rfm_profile", None)
    return (profile.segment_label if profile else "") or "—"


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
        return _segment_label(obj)

    def get_bonus(self, obj) -> int:
        return int(obj.bonuses or 0)

    def get_ltv(self, obj) -> int:
        return int(obj.total_spent or 0)

    def get_lastOrder(self, obj):
        return _last_order_iso(obj)

    def get_tags(self, obj) -> list[str]:
        return _tags(obj)
