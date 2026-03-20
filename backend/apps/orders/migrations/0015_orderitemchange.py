import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0014_seed_delivery_zones"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderItemChange",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("batch_id", models.UUIDField(default=uuid.uuid4, verbose_name="ID пакета изменений")),
                ("product_code", models.CharField(max_length=50, verbose_name="Код товара")),
                ("product_name", models.CharField(max_length=255, verbose_name="Название товара")),
                ("old_quantity", models.PositiveIntegerField(verbose_name="Было")),
                ("new_quantity", models.IntegerField(verbose_name="Стало")),
                ("price_at_moment", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Цена на момент заказа")),
                ("change_type", models.CharField(choices=[("decreased", "Уменьшено"), ("removed", "Удалено")], max_length=20, verbose_name="Тип изменения")),
                ("source", models.CharField(default="onec", max_length=20, verbose_name="Источник")),
                ("changed_at", models.DateTimeField(auto_now_add=True, verbose_name="Когда")),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="item_changes", to="orders.order")),
            ],
            options={
                "verbose_name": "Изменение позиции заказа",
                "verbose_name_plural": "Изменения позиций заказов",
                "db_table": "order_item_changes",
                "ordering": ["-changed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="orderitemchange",
            index=models.Index(fields=["order", "-changed_at"], name="oic_order_changed_idx"),
        ),
        migrations.AddIndex(
            model_name="orderitemchange",
            index=models.Index(fields=["batch_id"], name="oic_batch_idx"),
        ),
    ]
