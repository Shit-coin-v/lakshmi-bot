from django.contrib import admin

from apps.common.models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Доставка", {
            "fields": ("delivery_enabled", "delivery_disabled_message"),
        }),
        ("Самовывоз", {
            "fields": ("pickup_enabled", "pickup_disabled_message"),
        }),
    )

    def has_add_permission(self, request):
        # Singleton: если запись уже есть — не даём создавать ещё
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
