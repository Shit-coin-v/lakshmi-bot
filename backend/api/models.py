from django.db import models
from main.models import CustomUser


class OneCClientMap(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)  # FK на customers.id
    one_c_guid = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 

    class Meta:
        db_table = "api_onec_client_map"

class ReceiptDedup(models.Model):
    receipt_guid = models.CharField(max_length=64, unique=True)
    idempotency_key = models.CharField(max_length=64, null=True, blank=True)
    response_json = models.JSONField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = "api_receipt_dedup"
