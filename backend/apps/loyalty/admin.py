from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'total_amount', 'bonus_earned', 'purchase_date', 'store_id', 'purchase_type')
    list_filter = ('is_promotional', 'store_id', 'purchase_type')
    search_fields = ('customer__full_name', 'product__name')
    date_hierarchy = 'purchase_date'
