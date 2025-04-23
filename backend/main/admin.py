import asyncio
import logging

from django.contrib import admin, messages
from django.db.models import Count

from .models import *
from broadcast import send_broadcast_message


logger = logging.getLogger(__name__)


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
        'registration_date'
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
    list_display = ('customer', 'total_amount', 'bonus_earned', 'purchase_date', 'store')
    list_filter = ('is_promotional', 'store')
    search_fields = ('customer__full_name', 'product__name')
    date_hierarchy = 'purchase_date'


@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "message_text", "created_at", "is_sent", "send_to_all", "target_user_id")
    actions = ["send_broadcast"]

    def send_broadcast(self, request, queryset):
        success_count = 0
        fail_count = 0

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            for message in queryset:
                if not message.is_sent:
                    try:
                        loop.run_until_complete(send_broadcast_message(message))
                        message.is_sent = True
                        message.save()
                        logger.info(f"✅ Успешно отправлено сообщение ID={message.id}")
                        success_count += 1
                    except Exception as e:
                        logger.error(f"❌ Ошибка при отправке сообщения ID={message.id}: {e}")
                        fail_count += 1
        finally:
            loop.close()

        if success_count:
            self.message_user(request, f"✅ Успешно отправлено: {success_count}", level=messages.SUCCESS)
        if fail_count:
            self.message_user(request, f"❌ Ошибок при отправке: {fail_count}", level=messages.ERROR)

    send_broadcast.short_description = "Отправить выбранные рассылки"


admin.site.register(StoreType, StoreTypeAdmin)
admin.site.register(Store, StoreAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Transaction, TransactionAdmin)
