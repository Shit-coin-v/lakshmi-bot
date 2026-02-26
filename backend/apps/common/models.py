from django.db import models


class SiteSettings(models.Model):
    """Singleton: global site settings."""

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
        # Singleton: always pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Deletion is forbidden

    @classmethod
    def load(cls):
        """Get settings (creates record with defaults if not found)."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
