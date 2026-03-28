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


class CustomerRFMHistory(models.Model):
    TRANSITION_CHOICES = (
        ("initial", "Initial"),
        ("segment_changed", "Segment Changed"),
        ("score_changed", "Score Changed"),
    )

    customer = models.ForeignKey(
        "main.CustomUser",
        on_delete=models.CASCADE,
        related_name="rfm_history",
    )
    segment_code = models.CharField("Сегмент", max_length=50)
    previous_segment_code = models.CharField(
        "Предыдущий сегмент", max_length=50, null=True, blank=True,
    )
    r_score = models.IntegerField("R-score")
    f_score = models.IntegerField("F-score")
    m_score = models.IntegerField("M-score")
    recency_days = models.IntegerField("Recency (дни)", null=True, blank=True)
    frequency_orders = models.IntegerField("Frequency (заказы)", default=0)
    monetary_total = models.DecimalField(
        "Monetary (сумма)", max_digits=12, decimal_places=2, default=0,
    )
    transition_type = models.CharField(
        "Тип перехода", max_length=20, choices=TRANSITION_CHOICES,
    )
    calculated_at = models.DateTimeField("Рассчитано")
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        db_table = "rfm_customer_rfm_history"
        ordering = ["-calculated_at", "-id"]
        indexes = [
            models.Index(fields=["customer", "calculated_at"], name="rfm_hist_customer_calc_idx"),
            models.Index(fields=["segment_code"], name="rfm_hist_segment_idx"),
            models.Index(fields=["previous_segment_code"], name="rfm_hist_prev_segment_idx"),
            models.Index(fields=["calculated_at"], name="rfm_hist_calc_at_idx"),
        ]

    def __str__(self):
        return f"{self.customer_id}: {self.previous_segment_code} → {self.segment_code} ({self.transition_type})"


class RFMSegmentSyncLog(models.Model):
    """Журнал batch-синхронизации RFM-сегментов в 1С. Одна запись на месяц."""

    class Status(models.TextChoices):
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        SUCCESS = "success"
        PARTIAL = "partial"      # часть chunks не доставлена
        FAILED = "failed"

    effective_month = models.DateField(unique=True)  # 2026-04-01
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_customers = models.IntegerField(default=0)
    total_chunks = models.IntegerField(default=0)
    chunks_sent = models.IntegerField(default=0)
    chunks_failed = models.IntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rfm_segment_sync_log"
        verbose_name = "Лог синхронизации RFM в 1С"
        verbose_name_plural = "Логи синхронизации RFM в 1С"

    def __str__(self):
        return f"{self.effective_month} — {self.status}"
