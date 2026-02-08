from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price_at_moment',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'status', 'products_price', 'delivery_price', 'total_price', 'fulfillment_type', 'created_at')
    list_filter = ('status', 'fulfillment_type', 'created_at')
    search_fields = ('id', 'phone', 'address')
    inlines = [OrderItemInline]
    readonly_fields = ('created_at',)
