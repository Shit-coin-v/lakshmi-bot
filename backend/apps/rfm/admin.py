from django.contrib import admin

from .models import CustomerBonusTier, CustomerRFMHistory, CustomerRFMProfile


@admin.register(CustomerBonusTier)
class CustomerBonusTierAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "tier",
        "segment_label_at_fixation",
        "effective_from",
        "effective_to",
        "created_at",
    )
    list_filter = ("tier", "effective_from")
    search_fields = (
        "customer__telegram_id",
        "customer__full_name",
    )
    readonly_fields = ("created_at",)


@admin.register(CustomerRFMProfile)
class CustomerRFMProfileAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "rfm_code",
        "segment_label",
        "r_score",
        "f_score",
        "m_score",
        "recency_days",
        "frequency_count",
        "monetary_value",
        "calculated_at",
    )
    list_filter = ("segment_label", "r_score", "f_score", "m_score")
    search_fields = (
        "customer__telegram_id",
        "customer__full_name",
        "customer__phone",
    )
    readonly_fields = (
        "recency_days",
        "frequency_count",
        "monetary_value",
        "r_score",
        "f_score",
        "m_score",
        "rfm_code",
        "segment_label",
        "calculated_at",
        "created_at",
        "updated_at",
    )


@admin.register(CustomerRFMHistory)
class CustomerRFMHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "segment_code",
        "previous_segment_code",
        "transition_type",
        "calculated_at",
    )
    list_filter = ("transition_type", "segment_code")
    search_fields = ("customer__telegram_id",)
    readonly_fields = (
        "customer",
        "segment_code",
        "previous_segment_code",
        "r_score",
        "f_score",
        "m_score",
        "recency_days",
        "frequency_orders",
        "monetary_total",
        "transition_type",
        "calculated_at",
        "created_at",
    )
