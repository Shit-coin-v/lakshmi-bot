from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import (
    Campaign,
    CampaignRule,
    CustomerCampaignAssignment,
    CustomerSegment,
)
from .services import CampaignError, assign_campaign_to_customers


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "segment_type", "is_active", "updated_at")
    search_fields = ("name", "slug")
    list_filter = ("segment_type", "is_active")


# --- CampaignRule admin form с M2M валидацией ---

class CampaignRuleAdminForm(forms.ModelForm):
    """Form с валидацией M2M products и взаимоисключаемости с category."""

    class Meta:
        model = CampaignRule
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Убираем replace_base из доступных choices в форме
        if "stacking_mode" in self.fields:
            self.fields["stacking_mode"].choices = [
                c for c in self.fields["stacking_mode"].choices
                if c[0] != "replace_base"
            ]

    def clean(self):
        cleaned = super().clean()
        errors = {}

        products_m2m = cleaned.get("products")
        category = cleaned.get("category")
        legacy_product = cleaned.get("product")

        has_products_m2m = bool(products_m2m.exists()) if hasattr(products_m2m, 'exists') else bool(products_m2m)
        has_category = category is not None
        has_legacy = legacy_product is not None

        # Допустим только один тип товарного фильтра
        filter_count = sum([has_legacy, has_products_m2m, has_category])
        if filter_count > 1:
            if has_products_m2m and has_category:
                errors["category"] = "Нельзя указать одновременно товары (M2M) и категорию."
            if has_legacy and has_category:
                errors["product"] = "Нельзя указать одновременно product и category."
            if has_legacy and has_products_m2m:
                errors["product"] = "Нельзя указать одновременно product (legacy) и products (M2M)."

        # product_discount требует хотя бы один товарный фильтр
        reward_type = cleaned.get("reward_type")
        if reward_type == "product_discount" and filter_count == 0:
            errors["product"] = (
                "Для product_discount обязателен товарный фильтр: "
                "product, products или category."
            )

        # Проверка one_c_guid для products M2M
        if has_products_m2m:
            missing = [p.name for p in products_m2m if not p.one_c_guid]
            if missing:
                errors["products"] = (
                    f"У следующих товаров отсутствует one_c_guid: {', '.join(missing)}. "
                    "Все товары должны иметь 1С идентификатор."
                )

        # Проверка external_id для category
        if has_category and not category.external_id:
            errors["category"] = "У категории отсутствует external_id (1С идентификатор)."

        # Проверка one_c_guid для legacy product
        if has_legacy and not legacy_product.one_c_guid:
            errors["product"] = "У товара отсутствует one_c_guid (1С идентификатор)."

        # replace_base запрещён
        if cleaned.get("stacking_mode") == "replace_base":
            errors["stacking_mode"] = "Режим replace_base не поддерживается в v1."

        if errors:
            raise ValidationError(errors)

        return cleaned


class CampaignRuleInline(admin.TabularInline):
    model = CampaignRule
    form = CampaignRuleAdminForm
    extra = 1


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
        "segment",
        "start_at",
        "end_at",
        "priority",
        "is_active",
    )
    search_fields = ("name", "slug")
    list_filter = ("is_active", "one_time_use", "segment")
    inlines = [CampaignRuleInline]
    actions = ["assign_audience"]

    @admin.action(description="Назначить аудиторию кампании")
    def assign_audience(self, request, queryset):
        for campaign in queryset:
            try:
                result = assign_campaign_to_customers(campaign.id)
                self.message_user(
                    request,
                    f"Кампания «{campaign.name}»: "
                    f"назначено {result['created_assignments']}, "
                    f"пропущено (уже назначены) {result['skipped_existing']}, "
                    f"пропущено (пересечение) {result['skipped_overlapping']}, "
                    f"пропущено (opt-out) {result['skipped_opted_out']}.",
                    messages.SUCCESS,
                )
            except CampaignError as e:
                self.message_user(request, str(e), messages.ERROR)


@admin.register(CampaignRule)
class CampaignRuleAdmin(admin.ModelAdmin):
    form = CampaignRuleAdminForm
    list_display = (
        "id",
        "campaign",
        "reward_type",
        "reward_value",
        "reward_percent",
        "stacking_mode",
        "is_active",
    )
    list_filter = ("reward_type", "stacking_mode", "is_active")
    search_fields = ("campaign__name",)


@admin.register(CustomerCampaignAssignment)
class CustomerCampaignAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "campaign",
        "assigned_at",
        "used",
        "receipt_id",
        "synced_to_onec",
        "push_sent",
    )
    list_filter = ("used", "synced_to_onec", "push_sent", "campaign")
    search_fields = (
        "customer__telegram_id",
        "customer__full_name",
        "campaign__name",
    )
