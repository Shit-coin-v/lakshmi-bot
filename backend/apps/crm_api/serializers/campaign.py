"""Сериализаторы для списка кампаний CRM."""
from rest_framework import serializers

from apps.campaigns.models import Campaign


class CampaignListSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    period = serializers.SerializerMethodField()
    reach = serializers.IntegerField(read_only=True)  # из annotate
    used = serializers.IntegerField(read_only=True)   # из annotate
    segment = serializers.SerializerMethodField()
    audience = serializers.SerializerMethodField()
    rules = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "slug", "status",
            "period", "reach", "used", "segment", "audience", "rules", "priority",
        ]

    def get_id(self, obj) -> str:
        return f"CMP-{obj.id}"

    def get_status(self, obj) -> str:
        return "active" if obj.is_active else "finished"

    def get_period(self, obj) -> dict:
        return {
            "from": obj.start_at.date().isoformat() if obj.start_at else None,
            "to": obj.end_at.date().isoformat() if obj.end_at else None,
        }

    def get_segment(self, obj) -> str:
        if obj.rfm_segment:
            return obj.rfm_segment
        return obj.segment.name if obj.segment_id else ""

    def get_audience(self, obj) -> str:
        if obj.rfm_segment:
            return f"RFM: {obj.rfm_segment}"
        if obj.segment_id:
            return f"Сегмент: {obj.segment.name}"
        return "Все клиенты"

    def get_rules(self, obj) -> str:
        # obj.rules — RelatedManager; используем prefetch (см. queryset)
        first = next(iter(obj.rules.all()), None)
        if not first:
            return ""
        if first.reward_percent:
            return f"{first.reward_percent}% бонусов"
        if first.reward_value:
            return f"+{int(first.reward_value)} бонусов"
        return first.reward_type
