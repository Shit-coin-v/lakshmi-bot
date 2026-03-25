from rest_framework import serializers

from .models import CustomUser


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'telegram_id',
            'full_name',
            'phone',
            'email',
            'bonuses',
            'qr_code',
            'card_id',
            'avatar',
            'email_verified',
            'newsletter_enabled',
            'promo_enabled',
            'news_enabled',
            'general_enabled',
            'order_status_enabled',
        ]
        read_only_fields = ['id', 'telegram_id', 'bonuses', 'qr_code', 'card_id', 'email_verified']
