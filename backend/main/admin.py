from django.contrib import admin
from .models import *


class StoreTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'percent')
    search_fields = ('name',)


class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'type')
    list_filter = ('type',)
    search_fields = ('name',)


class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_code', 'price', 'stock', 'is_promotional')
    list_filter = ('category', 'is_promotional')
    search_fields = ('name', 'product_code')
    readonly_fields = ('updated_at',)


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'telegram_id', 'bonuses', 'qr_code', 'registration_date')
    search_fields = ('full_name', 'telegram_id')
    readonly_fields = ('registration_date',)


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'total_amount', 'bonus_earned', 'purchase_date', 'store')
    list_filter = ('is_promotional', 'store')
    search_fields = ('customer__full_name', 'product__name')
    date_hierarchy = 'purchase_date'


admin.site.register(StoreType, StoreTypeAdmin)
admin.site.register(Store, StoreAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Transaction, TransactionAdmin)
