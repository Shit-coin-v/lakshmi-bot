from rest_framework import serializers

from .models import Campaign, CampaignRule, CustomerCampaignAssignment


# ---------------------------------------------------------------------------
# Serializers для endpoint customer-promo (1С интеграция)
# ---------------------------------------------------------------------------

class _ProductConditionSerializer(serializers.Serializer):
    one_c_guid = serializers.CharField()
    name = serializers.CharField()


class _CategoryConditionSerializer(serializers.Serializer):
    external_id = serializers.CharField()
    name = serializers.CharField()


class _CampaignConditionsSerializer(serializers.Serializer):
    min_purchase_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, allow_null=True,
    )
    product = _ProductConditionSerializer(allow_null=True, default=None)
    products = _ProductConditionSerializer(many=True, allow_null=True, default=None)
    category = _CategoryConditionSerializer(allow_null=True, default=None)


class CampaignPromoBlockSerializer(serializers.Serializer):
    campaign_id = serializers.IntegerField()
    campaign_name = serializers.CharField()
    reward_type = serializers.CharField()
    reward_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    reward_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True,
    )
    stacking_mode = serializers.CharField()
    one_time_use = serializers.BooleanField()
    conditions = _CampaignConditionsSerializer()


class CustomerPromoResponseSerializer(serializers.Serializer):
    found = serializers.BooleanField()
    bonus_tier = serializers.CharField(allow_null=True)
    bonus_tier_effective_from = serializers.DateField(allow_null=True)
    bonus_tier_effective_to = serializers.DateField(allow_null=True)
    campaign = CampaignPromoBlockSerializer(allow_null=True)


class CampaignRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignRule
        fields = (
            "id",
            "reward_type",
            "reward_value",
            "reward_percent",
            "product_id",
            "min_purchase_amount",
            "stacking_mode",
            "is_active",
        )
        read_only_fields = fields


class CampaignSerializer(serializers.ModelSerializer):
    rules = CampaignRuleSerializer(many=True, read_only=True)

    class Meta:
        model = Campaign
        fields = (
            "id",
            "name",
            "slug",
            "push_title",
            "push_body",
            "start_at",
            "end_at",
            "one_time_use",
            "priority",
            "is_active",
            "rules",
        )
        read_only_fields = fields


class UserAssignedCampaignSerializer(serializers.ModelSerializer):
    campaign = CampaignSerializer(read_only=True)

    class Meta:
        model = CustomerCampaignAssignment
        fields = (
            "assigned_at",
            "used",
            "used_at",
            "push_sent",
            "push_sent_at",
            "campaign",
        )
        read_only_fields = fields
