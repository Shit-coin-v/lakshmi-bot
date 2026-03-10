from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class CustomerSegment(models.Model):
    SEGMENT_TYPE_CHOICES = (
        ("manual", "Ручной"),
        ("rule_based", "По правилам"),
    )

    name = models.CharField("Название", max_length=255)
    slug = models.SlugField("Код", max_length=255, unique=True)
    segment_type = models.CharField(
        "Тип сегмента",
        max_length=20,
        choices=SEGMENT_TYPE_CHOICES,
        default="manual",
    )
    rules = models.JSONField("Правила", default=dict, blank=True)
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        db_table = "customer_segments"
        verbose_name = "Сегмент клиентов"
        verbose_name_plural = "Сегменты клиентов"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Campaign(models.Model):
    name = models.CharField("Название", max_length=255)
    slug = models.SlugField("Код", max_length=255, unique=True)
    segment = models.ForeignKey(
        CustomerSegment,
        on_delete=models.PROTECT,
        related_name="campaigns",
        verbose_name="Сегмент",
    )
    push_title = models.CharField("Заголовок push", max_length=200)
    push_body = models.TextField("Текст push")
    start_at = models.DateTimeField("Начало")
    end_at = models.DateTimeField("Окончание")
    one_time_use = models.BooleanField("Одноразовая", default=False)
    priority = models.IntegerField("Приоритет", default=100)
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    class Meta:
        db_table = "campaigns"
        verbose_name = "Кампания"
        verbose_name_plural = "Кампании"
        ordering = ["-priority", "-created_at"]

    def __str__(self):
        return self.name


class CampaignRule(models.Model):
    REWARD_TYPE_CHOICES = (
        ("fixed_bonus", "Фиксированный бонус"),
        ("bonus_percent", "Процент бонусов"),
        ("fixed_plus_percent", "Фикс + процент"),
        ("product_discount", "Скидка на товар"),
    )
    STACKING_MODE_CHOICES = (
        ("stack_with_base", "Суммировать с базовым"),
        ("replace_base", "Заменить базовый"),
    )

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="rules",
        verbose_name="Кампания",
    )
    reward_type = models.CharField(
        "Тип награды",
        max_length=30,
        choices=REWARD_TYPE_CHOICES,
    )
    reward_value = models.DecimalField(
        "Значение награды",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
    )
    reward_percent = models.DecimalField(
        "Процент награды",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        "main.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_rules",
        verbose_name="Товар",
    )
    min_purchase_amount = models.DecimalField(
        "Мин. сумма покупки",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    stacking_mode = models.CharField(
        "Режим наложения",
        max_length=20,
        choices=STACKING_MODE_CHOICES,
        default="stack_with_base",
    )
    is_active = models.BooleanField("Активно", default=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        db_table = "campaign_rules"
        verbose_name = "Правило кампании"
        verbose_name_plural = "Правила кампаний"

    def __str__(self):
        return f"{self.campaign} — {self.get_reward_type_display()}"

    def clean(self):
        errors = {}

        if self.reward_type == "fixed_bonus":
            if not self.reward_value:
                errors["reward_value"] = "Обязательно для фиксированного бонуса."

        if self.reward_type == "bonus_percent":
            if not self.reward_percent:
                errors["reward_percent"] = "Обязательно для процента бонусов."

        if self.reward_type == "fixed_plus_percent":
            if not self.reward_value:
                errors["reward_value"] = "Обязательно для фикс + процент."
            if not self.reward_percent:
                errors["reward_percent"] = "Обязательно для фикс + процент."

        if self.reward_type == "product_discount":
            if not self.product:
                errors["product"] = "Обязательно для скидки на товар."
            if not self.reward_value or self.reward_value <= 0:
                errors["reward_value"] = "Размер скидки обязателен и должен быть больше 0."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CustomerCampaignAssignment(models.Model):
    customer = models.ForeignKey(
        "main.CustomUser",
        on_delete=models.CASCADE,
        related_name="campaign_assignments",
        verbose_name="Клиент",
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="assignments",
        verbose_name="Кампания",
    )
    assigned_at = models.DateTimeField("Назначена", auto_now_add=True)
    synced_to_onec = models.BooleanField("Синхронизировано в 1С", default=False)
    synced_at = models.DateTimeField("Дата синхронизации", null=True, blank=True)
    used = models.BooleanField("Использована", default=False)
    used_at = models.DateTimeField("Дата использования", null=True, blank=True)
    push_sent = models.BooleanField("Push отправлен", default=False)
    push_sent_at = models.DateTimeField("Дата отправки push", null=True, blank=True)

    class Meta:
        db_table = "customer_campaign_assignments"
        verbose_name = "Назначение кампании"
        verbose_name_plural = "Назначения кампаний"
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "campaign"],
                name="unique_customer_campaign",
            ),
        ]

    def __str__(self):
        return f"{self.customer} — {self.campaign}"
