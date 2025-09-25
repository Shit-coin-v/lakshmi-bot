from django.db import models
from django.utils import timezone


class Product(models.Model):
    product_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100, blank=True, null=True)
    stock = models.IntegerField(blank=True, null=True)
    store_id = models.IntegerField()
    is_promotional = models.BooleanField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    one_c_guid = models.CharField(max_length=64, unique=True, blank=True, null=True)

    class Meta:
        db_table = "products"

    def __str__(self):
        return self.name

class CustomUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    full_name = models.CharField(max_length=200, null=True, blank=True)
    birth_date = models.DateTimeField(null=True, blank=True)
    registration_date = models.DateTimeField(null=True, blank=True)
    qr_code = models.CharField(max_length=500, null=True, blank=True)
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
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "customers"

    def __str__(self):
        return self.full_name or f"User {self.telegram_id}"

class Transaction(models.Model):
    customer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    bonus_earned = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_time = models.TimeField(null=True, blank=True)
    store_id = models.IntegerField()
    is_promotional = models.BooleanField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchased_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.UUIDField(unique=True, null=True, blank=True)
    receipt_total_amount   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    receipt_discount_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    receipt_bonus_spent    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    receipt_bonus_earned   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    receipt_guid = models.CharField(max_length=64, null=True, blank=True)
    receipt_line = models.IntegerField()

    class Meta:
        db_table = "transactions"
        constraints = [
            models.UniqueConstraint(fields=["receipt_guid", "receipt_line"], name="uniq_receipt_line")
        ]

    def __str__(self):
        return f"Transaction #{self.id}"

class BroadcastMessage(models.Model):
    message_text = models.TextField("Текст сообщения", null=False)
    created_at = models.DateTimeField("Дата создания", default=timezone.now)
    send_to_all = models.BooleanField("Всем пользователям", default=True)
    target_user_ids = models.TextField(
        "ID пользователей (через запятую)",
        null=True,
        blank=True,
        help_text="Пример: 123456789, 987654321"
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
