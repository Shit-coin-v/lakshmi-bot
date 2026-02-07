from django.contrib import admin

from .models import CustomerDevice, Notification, NotificationOpenEvent


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "type", "title", "is_read", "created_at")
    list_filter = ("type", "is_read", "created_at")
    search_fields = ("title", "body", "user__full_name", "user__telegram_id")
    readonly_fields = ("created_at",)
    fields = ("user", "type", "title", "body", "is_read", "created_at")


@admin.register(NotificationOpenEvent)
class NotificationOpenEventAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "notification", "source", "occurred_at")
    list_filter = ("source", "occurred_at")
    search_fields = ("user__full_name", "user__telegram_id", "notification__title")
    readonly_fields = ("occurred_at",)


@admin.register(CustomerDevice)
class CustomerDeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "fcm_token", "platform", "created_at")
    list_filter = ("platform",)
    search_fields = ("customer__full_name", "customer__telegram_id", "fcm_token")
    readonly_fields = ("created_at", "updated_at")
