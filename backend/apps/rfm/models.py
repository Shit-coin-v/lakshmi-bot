from django.db import models


class CustomerRFMProfile(models.Model):
    customer = models.OneToOneField(
        "main.CustomUser",
        on_delete=models.CASCADE,
        related_name="rfm_profile",
        verbose_name="Клиент",
    )

    recency_days = models.IntegerField("Recency (дни)", null=True, blank=True)
    frequency_count = models.IntegerField("Frequency (покупки)", default=0)
    monetary_value = models.DecimalField(
        "Monetary (сумма)",
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    r_score = models.IntegerField("R-score", default=1)
    f_score = models.IntegerField("F-score", default=1)
    m_score = models.IntegerField("M-score", default=1)

    rfm_code = models.CharField("RFM-код", max_length=3, default="111")
    segment_label = models.CharField(
        "Сегмент",
        max_length=50,
        default="lost",
    )

    calculated_at = models.DateTimeField("Дата расчёта")
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        db_table = "customer_rfm_profiles"
        verbose_name = "RFM-профиль клиента"
        verbose_name_plural = "RFM-профили клиентов"
        ordering = ["-calculated_at"]

    def __str__(self):
        return f"{self.customer} — {self.rfm_code} ({self.segment_label})"
