from django.db import models
from apps.loyalty.models import CustomUser


class OneCClientMap(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="onec_client_maps",
    )
    one_c_guid = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "api_onec_client_map"
        verbose_name = "1С маппинг клиента"
        verbose_name_plural = "1С маппинги клиентов"

    def __str__(self):
        return f"user={self.user_id} guid={self.one_c_guid}"


class ReceiptDedup(models.Model):
    receipt_guid = models.CharField(max_length=64, unique=True)
    idempotency_key = models.CharField(max_length=64, null=True, blank=True)
    response_json = models.JSONField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = "api_receipt_dedup"
        verbose_name = "Дедупликация чека"
        verbose_name_plural = "Дедупликации чеков"

    def __str__(self):
        return self.receipt_guid
