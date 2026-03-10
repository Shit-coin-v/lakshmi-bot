from rest_framework import serializers

from .models import Campaign, CampaignRule, CustomerCampaignAssignment


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
