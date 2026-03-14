from django.contrib import admin

from .models import ProductRanking


@admin.register(ProductRanking)
class ProductRankingAdmin(admin.ModelAdmin):
    list_display = ("product", "customer", "score", "calculated_at")
    list_filter = ("calculated_at",)
    search_fields = (
        "product__name",
        "customer__full_name",
        "customer__phone",
    )
    readonly_fields = ("product", "customer", "score", "calculated_at")
    raw_id_fields = ("product", "customer")
