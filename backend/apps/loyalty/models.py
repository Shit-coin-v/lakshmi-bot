from django.db import models

# Backward-compat re-exports for code that imports from apps.loyalty.models
from apps.main.models import CustomUser, Product  # noqa: F401,E402

__all__ = ["CustomUser", "Product", "Transaction"]


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
