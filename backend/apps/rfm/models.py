from django.db import models


class CustomerBonusTier(models.Model):
    """Месячная фиксация бонусного статуса клиента.

    Фиксируется 1-го числа каждого месяца в 00:05 Asia/Yakutsk.
    Стабилен весь месяц: champions → 7%, standard → 5% (процент определяет 1С).
    """

    TIER_CHOICES = (
        ("champions", "Champions"),
        ("standard", "Standard"),
    )

    customer = models.ForeignKey(
        "main.CustomUser",
        on_delete=models.CASCADE,
        related_name="bonus_tiers",
        verbose_name="Клиент",
    )
    tier = models.CharField("Бонусный статус", max_length=20, choices=TIER_CHOICES)
    segment_label_at_fixation = models.CharField(
        "Сегмент при фиксации", max_length=50,
        help_text="segment_label, вычисленный при фиксации (аудит)",
    )
    effective_from = models.DateField("Начало действия")
    effective_to = models.DateField("Конец действия")
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        db_table = "customer_bonus_tiers"
        verbose_name = "Месячный бонусный статус"
        verbose_name_plural = "Месячные бонусные статусы"
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "effective_from"],
                name="unique_customer_bonus_tier_period",
            ),
        ]
        indexes = [
            models.Index(
                fields=["effective_from", "effective_to"],
                name="idx_bonus_tier_period",
            ),
        ]

    def __str__(self):
        return f"{self.customer} — {self.tier} ({self.effective_from}–{self.effective_to})"


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
