from django.db import models


class Notification(models.Model):
    TYPE_CHOICES = (
        ("personal", "Персональное"),
        ("broadcast", "Массовое"),
    )

    user = models.ForeignKey(
        "main.CustomUser",
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Клиент",
    )
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    body = models.TextField(verbose_name="Текст")
    is_read = models.BooleanField(default=False, db_index=True, verbose_name="Прочитано")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Создано")
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="personal",
        db_index=True,
        verbose_name="Тип",
    )

    class Meta:
        db_table = "notifications"
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        indexes = [
            models.Index(fields=["user", "-created_at"], name="notif_user_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} | {self.type} | {self.title}"


class NotificationOpenEvent(models.Model):
    SOURCE_CHOICES = (
        ("inapp", "In-app"),
        ("push", "Push"),
    )

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="open_events",
        verbose_name="Уведомление",
    )
    user = models.ForeignKey(
        "main.CustomUser",
        on_delete=models.CASCADE,
        related_name="notification_open_events",
        verbose_name="Клиент",
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="inapp",
        db_index=True,
        verbose_name="Источник",
    )
    occurred_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Открыто",
    )

    class Meta:
        db_table = "notification_open_events"
        verbose_name = "Открытие уведомления"
        verbose_name_plural = "Открытия уведомлений"
        constraints = [
            models.UniqueConstraint(
                fields=["notification"],
                name="uniq_notification_open_once",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id} | notif={self.notification_id} | {self.source}"


class CustomerDevice(models.Model):
    PLATFORM_CHOICES = (
        ("android", "Android"),
        ("ios", "iOS"),
        ("web", "Web"),
    )

    customer = models.ForeignKey(
        "main.CustomUser",
        on_delete=models.CASCADE,
        related_name="devices",
        verbose_name="Клиент",
    )
    fcm_token = models.CharField(max_length=255, unique=True, verbose_name="FCM токен")
    platform = models.CharField(
        max_length=20, choices=PLATFORM_CHOICES, default="android", verbose_name="Платформа"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлен")

    class Meta:
        db_table = "customer_devices"
        verbose_name = "Устройство клиента"
        verbose_name_plural = "Устройства клиентов"

    def __str__(self):
        return f"{self.customer_id} | {self.platform}"


class CourierNotificationMessage(models.Model):
    """Tracks Telegram message_ids sent to couriers by Celery, so the bot can delete them."""

    courier_tg_id = models.BigIntegerField(db_index=True)
    telegram_message_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "courier_notification_messages"
        verbose_name = "Уведомление курьеру"
        verbose_name_plural = "Уведомления курьерам"

    def __str__(self):
        return f"courier={self.courier_tg_id} msg={self.telegram_message_id}"


class PickerNotificationMessage(models.Model):
    """Tracks Telegram message_ids sent to pickers by Celery, so the bot can delete them."""

    picker_tg_id = models.BigIntegerField(db_index=True)
    telegram_message_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "picker_notification_messages"
        verbose_name = "Уведомление сборщику"
        verbose_name_plural = "Уведомления сборщикам"

    def __str__(self):
        return f"picker={self.picker_tg_id} msg={self.telegram_message_id}"
