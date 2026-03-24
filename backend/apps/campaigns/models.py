from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.rfm.constants import RFM_SEGMENT_CHOICES


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
    AUDIENCE_TYPE_CHOICES = [
        ("customer_segment", "Сегмент клиентов"),
        ("rfm_segment", "RFM-сегмент"),
    ]

    name = models.CharField("Название", max_length=255)
    slug = models.SlugField("Код", max_length=255, unique=True)
    audience_type = models.CharField(
        "Источник аудитории",
        max_length=20,
        choices=AUDIENCE_TYPE_CHOICES,
        default="customer_segment",
    )
    segment = models.ForeignKey(
        CustomerSegment,
        on_delete=models.PROTECT,
        related_name="campaigns",
        verbose_name="Сегмент клиентов",
        null=True,
        blank=True,
        help_text="Заполните при источнике аудитории «Сегмент клиентов».",
    )
    rfm_segment = models.CharField(
        "RFM-сегмент",
        max_length=50,
        choices=RFM_SEGMENT_CHOICES,
        null=True,
        blank=True,
        help_text="Заполните при источнике аудитории «RFM-сегмент».",
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
        constraints = [
            # audience_type допускает только известные значения
            models.CheckConstraint(
                check=models.Q(audience_type__in=["customer_segment", "rfm_segment"]),
                name="campaign_valid_audience_type",
            ),
            # customer_segment → segment обязателен, rfm_segment пустой
            models.CheckConstraint(
                check=(
                    ~models.Q(audience_type="customer_segment")
                    | (
                        models.Q(segment__isnull=False)
                        & (models.Q(rfm_segment__isnull=True) | models.Q(rfm_segment=""))
                    )
                ),
                name="campaign_cs_requires_segment",
            ),
            # rfm_segment → rfm_segment заполнен из допустимых значений, segment пустой
            models.CheckConstraint(
                check=(
                    ~models.Q(audience_type="rfm_segment")
                    | (
                        models.Q(segment__isnull=True)
                        & models.Q(rfm_segment__in=[c[0] for c in RFM_SEGMENT_CHOICES])
                    )
                ),
                name="campaign_rfm_requires_valid_rfm_segment",
            ),
        ]

    def clean(self):
        errors = {}
        if self.audience_type == "customer_segment":
            if not self.segment_id:
                errors["segment"] = "Обязательно при источнике аудитории «Сегмент клиентов»."
            if self.rfm_segment:
                errors["rfm_segment"] = "Должно быть пустым при источнике аудитории «Сегмент клиентов»."
        elif self.audience_type == "rfm_segment":
            if not self.rfm_segment:
                errors["rfm_segment"] = "Обязательно при источнике аудитории «RFM-сегмент»."
            if self.segment_id:
                errors["segment"] = "Должно быть пустым при источнике аудитории «RFM-сегмент»."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

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
        ("replace_base", "Заменить базовый (не поддерживается v1)"),
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
        verbose_name="Товар (deprecated, используйте products)",
    )
    products = models.ManyToManyField(
        "main.Product",
        blank=True,
        related_name="campaign_rules_m2m",
        verbose_name="Товары",
    )
    category = models.ForeignKey(
        "main.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_rules",
        verbose_name="Категория",
        help_text="Включает все дочерние подкатегории. Дерево разворачивает 1С.",
    )
    min_purchase_amount = models.DecimalField(
        "Мин. сумма покупки (после скидок)",
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
        constraints = [
            models.UniqueConstraint(
                fields=["campaign"],
                condition=models.Q(is_active=True),
                name="unique_active_rule_per_campaign",
            ),
        ]

    def __str__(self):
        return f"{self.campaign} — {self.get_reward_type_display()}"

    def clean(self):
        errors = {}

        # --- reward_type валидация ---
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
            if not self.reward_value or self.reward_value <= 0:
                errors["reward_value"] = "Размер скидки обязателен и должен быть больше 0."
            # product_discount требует хотя бы один товарный фильтр.
            # product (legacy FK) и category проверяем здесь;
            # products M2M проверяется на уровне admin form (M2M недоступна в clean до save).
            has_any_filter = self.product_id is not None or self.category_id is not None
            if not has_any_filter and not self.pk:
                # Новый объект без FK-фильтров. M2M ещё не сохранена —
                # не блокируем здесь, admin form проверит полную картину.
                pass
            elif not has_any_filter and self.pk:
                # Существующий объект: можем проверить M2M
                if not self.products.exists():
                    errors["product"] = (
                        "Для product_discount обязателен товарный фильтр: "
                        "product, products или category."
                    )

        # --- v1: replace_base не поддерживается ---
        if self.stacking_mode == "replace_base":
            errors["stacking_mode"] = (
                "Режим replace_base не поддерживается в v1. "
                "Используйте stack_with_base."
            )

        # --- Допустим только один тип товарного фильтра ---
        has_category = self.category_id is not None
        has_legacy_product = self.product_id is not None

        if has_legacy_product and has_category:
            errors["product"] = (
                "Нельзя указать одновременно product и category. "
                "Допустим только один товарный фильтр."
            )

        # --- валидация 1С идентификаторов (для FK полей, проверяемых в clean) ---
        if has_legacy_product and self.product and not self.product.one_c_guid:
            errors["product"] = "У товара отсутствует one_c_guid (1С идентификатор)."

        if has_category and self.category and not self.category.external_id:
            errors["category"] = "У категории отсутствует external_id (1С идентификатор)."

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
    receipt_id = models.CharField(
        "ID чека (1С)", max_length=100, null=True, blank=True,
        help_text="Внешний идентификатор чека из 1С для аудита",
    )
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
