from django.contrib import admin

from .models import CourierProfile, DeliveryZone, Order, OrderItem, PickerProfile


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price_at_moment',)


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_code', 'sort_order', 'is_active', 'is_default')
    list_editable = ('sort_order', 'is_active', 'is_default')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'status', 'products_price', 'delivery_price', 'total_price', 'fulfillment_type', 'created_at')
    list_filter = ('status', 'fulfillment_type', 'created_at')
    search_fields = ('id', 'phone', 'address')
    inlines = [OrderItemInline]
    readonly_fields = ('created_at',)


@admin.register(CourierProfile)
class CourierProfileAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'full_name', 'phone', 'is_approved', 'is_blacklisted', 'accepting_orders', 'created_at')
    list_filter = ('is_approved', 'is_blacklisted', 'accepting_orders')
    search_fields = ('full_name', 'phone', 'telegram_id')
    list_editable = ('is_approved', 'is_blacklisted')
    actions = ['approve', 'blacklist', 'unblacklist']

    @admin.action(description="Подтвердить выбранных")
    def approve(self, request, queryset):
        for obj in queryset:
            obj.is_approved = True
            obj.save(update_fields=["is_approved"])

    @admin.action(description="Добавить в чёрный список")
    def blacklist(self, request, queryset):
        for obj in queryset:
            obj.is_blacklisted = True
            obj.is_approved = False
            obj.save(update_fields=["is_blacklisted", "is_approved"])

    @admin.action(description="Убрать из чёрного списка")
    def unblacklist(self, request, queryset):
        for obj in queryset:
            obj.is_blacklisted = False
            obj.save(update_fields=["is_blacklisted"])


@admin.register(PickerProfile)
class PickerProfileAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'full_name', 'phone', 'is_approved', 'is_blacklisted', 'created_at')
    list_filter = ('is_approved', 'is_blacklisted')
    search_fields = ('full_name', 'phone', 'telegram_id')
    list_editable = ('is_approved', 'is_blacklisted')
    actions = ['approve', 'blacklist', 'unblacklist']

    @admin.action(description="Подтвердить выбранных")
    def approve(self, request, queryset):
        for obj in queryset:
            obj.is_approved = True
            obj.save(update_fields=["is_approved"])

    @admin.action(description="Добавить в чёрный список")
    def blacklist(self, request, queryset):
        for obj in queryset:
            obj.is_blacklisted = True
            obj.is_approved = False
            obj.save(update_fields=["is_blacklisted", "is_approved"])

    @admin.action(description="Убрать из чёрного списка")
    def unblacklist(self, request, queryset):
        for obj in queryset:
            obj.is_blacklisted = False
            obj.save(update_fields=["is_blacklisted"])
