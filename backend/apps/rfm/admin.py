from django.contrib import admin

from .models import CustomerRFMProfile


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
