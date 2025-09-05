from django.db import models
from main.models import CustomUser


class OneCClientMap(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='onec_links')
    one_c_guid = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_onec_client_map'
        indexes = [models.Index(fields=['one_c_guid'])]

class ReceiptDedup(models.Model):
    receipt_guid = models.CharField(max_length=64, unique=True)
    idempotency_key = models.CharField(max_length=64, null=True, blank=True)
    response_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_receipt_dedup'
        indexes = [models.Index(fields=['created_at'])]

# Create your models here.
