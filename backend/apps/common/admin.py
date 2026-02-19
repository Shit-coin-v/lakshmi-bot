from django.contrib import admin
from django.shortcuts import redirect

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
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Singleton: автосоздание + редирект на единственную запись
        obj = SiteSettings.load()
        return redirect(
            f"{request.path}{obj.pk}/change/"
        )
