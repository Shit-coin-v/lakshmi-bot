from django.db import models

# Backward-compat re-exports for code that imports from apps.loyalty.models
from apps.main.models import CustomUser, Product  # noqa: F401,E402

__all__ = ["CustomUser", "Product", "PurchaseType", "ReferralReward", "Transaction"]


class PurchaseType(models.TextChoices):
    DELIVERY = "delivery", "Доставка"
    PICKUP = "pickup", "Самовывоз"
    IN_STORE = "in_store", "Покупка в магазине"


class Transaction(models.Model):
    customer = models.ForeignKey("main.CustomUser", on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey("main.Product", on_delete=models.SET_NULL, null=True, blank=True)
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
    receipt_total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    receipt_discount_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    receipt_bonus_spent = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    receipt_bonus_earned = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    receipt_guid = models.CharField(max_length=64, null=True, blank=True)
    receipt_line = models.IntegerField(null=True, blank=True)
    purchase_type = models.CharField(
        "Тип покупки",
        max_length=20,
        choices=PurchaseType.choices,
        default=PurchaseType.IN_STORE,
    )

    class Meta:
        db_table = "transactions"
        constraints = [
            models.UniqueConstraint(fields=["receipt_guid", "receipt_line"], name="uniq_receipt_line")
        ]
        indexes = [
            models.Index(fields=["customer"], name="transaction_customer_idx"),
        ]

    def __str__(self):
        return f"Transaction #{self.id}"


class ReferralReward(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает отправки"
        SUCCESS = "success", "Успешно"
        FAILED = "failed", "Ошибка"

    # Кто пригласил (получатель бонуса)
    referrer = models.ForeignKey(
        "main.CustomUser",
        on_delete=models.CASCADE,
        related_name="referral_rewards_given",
    )
    # Кого пригласили (чья покупка триггернула бонус)
    referee = models.ForeignKey(
        "main.CustomUser",
        on_delete=models.CASCADE,
        related_name="referral_reward_received",
    )

    bonus_amount = models.DecimalField(max_digits=10, decimal_places=2, default=50)
    receipt_guid = models.CharField("GUID чека-триггера", max_length=100)
    source = models.CharField(
        "Источник связи",
        max_length=20,
        choices=[("app", "Приложение"), ("telegram", "Telegram"), ("manual", "Ручное")],
    )

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    last_error = models.TextField(blank=True, default="")
    attempts = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "referral_rewards"
        constraints = [
            models.UniqueConstraint(
                fields=["referee"],
                name="one_referral_reward_per_referee",
            ),
        ]

    def __str__(self):
        return f"ReferralReward #{self.id} referrer={self.referrer_id} referee={self.referee_id}"
