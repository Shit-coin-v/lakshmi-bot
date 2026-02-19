from django.db import models


class SiteSettings(models.Model):
    """Singleton: глобальные настройки сайта."""

    delivery_enabled = models.BooleanField(
        default=True,
        verbose_name="Доставка включена",
    )
    delivery_disabled_message = models.TextField(
        blank=True,
        default="",
        verbose_name="Сообщение при выключенной доставке",
        help_text="Показывается клиенту при попытке оформить доставку",
    )
    pickup_enabled = models.BooleanField(
        default=True,
        verbose_name="Самовывоз включён",
    )
    pickup_disabled_message = models.TextField(
        blank=True,
        default="",
        verbose_name="Сообщение при выключенном самовывозе",
        help_text="Показывается клиенту при попытке оформить самовывоз",
    )

    class Meta:
        verbose_name = "Настройки доставки"
        verbose_name_plural = "Настройки доставки"

    def __str__(self):
        return "Настройки доставки"

    def save(self, *args, **kwargs):
        # Singleton: всегда pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Запрет удаления

    @classmethod
    def load(cls):
        """Получить настройки (создаёт запись с defaults если нет)."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
