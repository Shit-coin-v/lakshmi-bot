from django.db import models
from django.utils import timezone


class Product(models.Model):
    product_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100, blank=True, null=True)
    stock = models.IntegerField(blank=True, null=True)
    store_id = models.IntegerField()
    image = models.ImageField(upload_to='products/', null=True, blank=True, verbose_name="Фото")
    description = models.TextField(null=True, blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    is_promotional = models.BooleanField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    one_c_guid = models.CharField(max_length=64, unique=True, blank=True, null=True)

    class Meta:
        db_table = "products"
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self):
        return self.name

class CustomUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    full_name = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Телефон")
    email = models.EmailField(null=True, blank=True, verbose_name="Email")
    birth_date = models.DateTimeField(null=True, blank=True)
    registration_date = models.DateTimeField(null=True, blank=True)
    qr_code = models.CharField(max_length=500, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Аватар")
    bonuses = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    referrer = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals",
        db_column="referrer_id",
        to_field="telegram_id"
    )
    last_purchase_date = models.DateTimeField(null=True, blank=True)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchase_count = models.IntegerField(null=True, blank=True)
    personal_data_consent = models.BooleanField(null=True, blank=True)
    newsletter_enabled = models.BooleanField("Подписка на рассылки", default=True)
    promo_enabled = models.BooleanField("Акции и скидки", default=True)
    news_enabled = models.BooleanField("Новости магазина", default=True)
    general_enabled = models.BooleanField("Общие уведомления", default=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "customers"
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"

    def __str__(self):
        return self.full_name or f"User {self.telegram_id}"


class BroadcastMessage(models.Model):
    CATEGORY_CHOICES = (
        ("general", "Общая"),
        ("promo", "Акции и скидки"),
        ("news", "Новости магазина"),
    )

    message_text = models.TextField("Текст сообщения", null=False)
    created_at = models.DateTimeField("Дата создания", default=timezone.now)
    send_to_all = models.BooleanField("Всем пользователям", default=True)
    target_user_ids = models.TextField(
        "ID пользователей (через запятую)",
        null=True,
        blank=True,
        help_text="Пример: 123456789, 987654321"
    )
    category = models.CharField(
        "Категория",
        max_length=10,
        choices=CATEGORY_CHOICES,
        default="general",
    )

    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        db_table = 'broadcast_messages'
        ordering = ['-created_at']


class BotActivity(models.Model):
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bot_activities')
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'История'
        verbose_name_plural = 'Истории'
        db_table = 'bot_activities'

    def __str__(self):
        return f"{self.customer}: {self.action} at {self.timestamp}"


class NewsletterDelivery(models.Model):
    CHANNEL_CHOICES = (
        ("telegram", "Telegram"),
        ("push", "Push"),
    )

    message = models.ForeignKey(
        BroadcastMessage,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="newsletter_deliveries",
    )
    chat_id = models.BigIntegerField(null=True, blank=True)
    telegram_message_id = models.BigIntegerField(null=True, blank=True)
    open_token = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    channel = models.CharField(
        "Канал доставки",
        max_length=10,
        choices=CHANNEL_CHOICES,
        default="telegram",
        db_index=True,
    )
    notification = models.ForeignKey(
        "notifications.Notification",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="newsletter_deliveries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "newsletter_deliveries"
        verbose_name = "Доставка рассылки"
        verbose_name_plural = "Доставки рассылок"
        indexes = [
            models.Index(fields=["message", "customer"], name="newsletter_delivery_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["message", "customer"],
                name="newsletter_delivery_uc",
            )
        ]

    def __str__(self):
        return f"Delivery #{self.id} for {self.customer_id}"


class NewsletterOpenEvent(models.Model):
    delivery = models.ForeignKey(
        NewsletterDelivery,
        on_delete=models.CASCADE,
        related_name="open_events",
    )
    occurred_at = models.DateTimeField(default=timezone.now)
    raw_callback_data = models.CharField(max_length=128, blank=True)
    telegram_user_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "newsletter_open_events"
        verbose_name = "Открытие рассылки"
        verbose_name_plural = "Открытия рассылок"
        indexes = [
            models.Index(fields=["delivery"], name="newsletter_open_delivery_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["delivery"],
                name="newsletter_open_events_delivery_key",
            )
        ]

    def __str__(self):
        return f"Open event #{self.id} for delivery {self.delivery_id}"


# Backward-compat imports (C10 refactoring) — DO NOT REMOVE
from apps.orders.models import Order, OrderItem  # noqa: F401,E402
from apps.loyalty.models import Transaction  # noqa: F401,E402
from apps.notifications.models import (  # noqa: F401,E402
    Notification,
    NotificationOpenEvent,
    CustomerDevice,
)
