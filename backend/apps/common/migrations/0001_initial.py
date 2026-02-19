from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SiteSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "delivery_enabled",
                    models.BooleanField(
                        default=True, verbose_name="Доставка включена"
                    ),
                ),
                (
                    "delivery_disabled_message",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Показывается клиенту при попытке оформить доставку",
                        verbose_name="Сообщение при выключенной доставке",
                    ),
                ),
                (
                    "pickup_enabled",
                    models.BooleanField(
                        default=True, verbose_name="Самовывоз включён"
                    ),
                ),
                (
                    "pickup_disabled_message",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Показывается клиенту при попытке оформить самовывоз",
                        verbose_name="Сообщение при выключенном самовывозе",
                    ),
                ),
            ],
            options={
                "verbose_name": "Настройки сайта",
                "verbose_name_plural": "Настройки сайта",
            },
        ),
    ]
