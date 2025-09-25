import asyncio
import logging

from django.contrib import admin, messages
from django.db.models import Count

from .models import *

logger = logging.getLogger(__name__)


class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_code', 'price', 'stock', 'is_promotional')
    list_filter = ('category', 'is_promotional')
    search_fields = ('name', 'product_code')
    readonly_fields = ('updated_at',)


class ReferralInline(admin.TabularInline):
    model = CustomUser
    fk_name = 'referrer'
    fields = ['telegram_id', 'full_name', 'registration_date']
    readonly_fields = ['telegram_id', 'full_name', 'registration_date']
    extra = 0
    can_delete = False
    show_change_link = False
    verbose_name = 'Реферал'
    verbose_name_plural = 'Рефералы'

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'telegram_id',
        'bonuses',
        'qr_code',
        'referrer',
        'get_referrals_count',
        'registration_date',
        'last_purchase_date',
        'total_spent',
        'purchase_count'
    )
    search_fields = ('full_name', 'telegram_id')
    readonly_fields = ('registration_date',)
    inlines = [ReferralInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(referrals_count=Count('referrals'))
        return queryset

    def get_referrals_count(self, obj):
        return obj.referrals_count

    get_referrals_count.admin_order_field = 'referrals_count'
    get_referrals_count.short_description = 'Кол-во рефералов'


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'total_amount', 'bonus_earned', 'purchase_date', 'store_id')
    list_filter = ('is_promotional', 'store_id')
    search_fields = ('customer__full_name', 'product__name')
    date_hierarchy = 'purchase_date'


@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "truncated_message", "created_at", "send_to_all", "target_user_ids")
    actions = ["send_broadcast"]
    fields = ('message_text', 'send_to_all', 'target_user_ids')

    def truncated_message(self, obj):
        return obj.message_text[:50] + "..." if len(obj.message_text) > 50 else obj.message_text

    truncated_message.short_description = "Текст сообщения"

    def send_broadcast(self, request, queryset):
        try:
            from src.broadcast import send_broadcast_message
        except RuntimeError as exc:
            self.message_user(request, str(exc), messages.ERROR)
            return
        except Exception as exc:
            logger.error("Failed to import broadcast helper: %s", exc)
            self.message_user(request, "Не удалось инициализировать рассылку", messages.ERROR)
            return

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        success = errors = 0
        for msg in queryset:
            try:
                loop.run_until_complete(send_broadcast_message(msg))
                success += 1
            except Exception as e:
                errors += 1
                logger.error(f"Ошибка рассылки {msg.id}: {str(e)}")

        if success:
            self.message_user(request, f"Успешно отправлено: {success}", messages.SUCCESS)
        if errors:
            self.message_user(request, f"Ошибок: {errors}", messages.ERROR)

    send_broadcast.short_description = "▶ Отправить выбранные рассылки"


@admin.register(BotActivity)
class BotActivityAdmin(admin.ModelAdmin):
    list_display = ('customer', 'action', 'timestamp')


admin.site.register(Product, ProductAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Transaction, TransactionAdmin)
