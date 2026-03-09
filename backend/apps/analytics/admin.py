from django.contrib import admin

from .models import AnalyticsEvent


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ("user", "event_type", "screen", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("user__telegram_id", "screen")
    readonly_fields = ("user", "event_type", "screen", "payload", "created_at")
    date_hierarchy = "created_at"
