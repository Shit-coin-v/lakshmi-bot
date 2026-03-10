from django.contrib import admin

from .models import (
    Campaign,
    CampaignRule,
    CustomerCampaignAssignment,
    CustomerSegment,
)


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "segment_type", "is_active", "updated_at")
    search_fields = ("name", "slug")
    list_filter = ("segment_type", "is_active")


class CampaignRuleInline(admin.TabularInline):
    model = CampaignRule
    extra = 1


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
        "segment",
        "start_at",
        "end_at",
        "priority",
        "is_active",
    )
    search_fields = ("name", "slug")
    list_filter = ("is_active", "one_time_use", "segment")
    inlines = [CampaignRuleInline]


@admin.register(CampaignRule)
class CampaignRuleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "campaign",
        "reward_type",
        "reward_value",
        "reward_percent",
        "stacking_mode",
        "is_active",
    )
    list_filter = ("reward_type", "stacking_mode", "is_active")
    search_fields = ("campaign__name",)


@admin.register(CustomerCampaignAssignment)
class CustomerCampaignAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "campaign",
        "assigned_at",
        "used",
        "synced_to_onec",
        "push_sent",
    )
    list_filter = ("used", "synced_to_onec", "push_sent", "campaign")
    search_fields = (
        "customer__telegram_id",
        "customer__username",
        "campaign__name",
    )
