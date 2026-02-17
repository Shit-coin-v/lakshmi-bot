from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0004_order_sync_idempotency_key"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "Новый"),
                    ("accepted", "Заказ принят"),
                    ("assembly", "Заказ собирается"),
                    ("ready", "Заказ собран"),
                    ("delivery", "Курьер забрал заказ и в пути"),
                    ("arrived", "Курьер пришёл и ждёт вас"),
                    ("completed", "Заказ доставлен"),
                    ("canceled", "Отменён"),
                ],
                default="new",
                max_length=20,
                verbose_name="Статус",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="assembled_by",
            field=models.BigIntegerField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name="Telegram ID сборщика",
            ),
        ),
    ]
