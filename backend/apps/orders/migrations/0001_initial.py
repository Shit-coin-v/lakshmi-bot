"""Create Order and OrderItem in orders app (C10 God Model fix).

State-only migration: no SQL executed. Tables already exist from main app migrations.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("main", "0027_move_order_to_orders"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Order",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("status", models.CharField(choices=[("new", "Новый"), ("assembly", "В сборке"), ("delivery", "Курьер едет"), ("completed", "Доставлен"), ("canceled", "Отменен")], default="new", max_length=20, verbose_name="Статус")),
                        ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                        ("address", models.TextField(verbose_name="Адрес доставки")),
                        ("phone", models.CharField(max_length=20, verbose_name="Телефон")),
                        ("comment", models.TextField(blank=True, null=True, verbose_name="Комментарий")),
                        ("products_price", models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="Сумма товаров")),
                        ("delivery_price", models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="Стоимость доставки")),
                        ("total_price", models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="Итого к оплате")),
                        ("payment_method", models.CharField(choices=[("card_courier", "Картой курьеру"), ("cash", "Наличными"), ("sbp", "СБП")], default="card_courier", max_length=20, verbose_name="Способ оплаты")),
                        ("fulfillment_type", models.CharField(choices=[("delivery", "Доставка"), ("pickup", "Самовывоз")], default="delivery", max_length=20, verbose_name="Способ получения")),
                        ("onec_guid", models.CharField(blank=True, db_index=True, max_length=64, null=True, verbose_name="GUID 1С")),
                        ("sync_status", models.CharField(db_index=True, default="new", max_length=20, verbose_name="Синхр. статус")),
                        ("sent_to_onec_at", models.DateTimeField(blank=True, null=True, verbose_name="Отправлен в 1С")),
                        ("last_sync_error", models.TextField(blank=True, null=True, verbose_name="Ошибка синхронизации")),
                        ("sync_attempts", models.IntegerField(default=0, verbose_name="Попыток синхронизации")),
                        ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="orders", to="main.customuser", verbose_name="Клиент")),
                    ],
                    options={
                        "verbose_name": "Заказ доставки",
                        "verbose_name_plural": "Заказы доставки",
                        "db_table": "orders",
                        "ordering": ["-created_at"],
                    },
                ),
                migrations.AddIndex(
                    model_name="order",
                    index=models.Index(fields=["customer", "-created_at"], name="order_customer_created_idx"),
                ),
                migrations.CreateModel(
                    name="OrderItem",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("quantity", models.IntegerField(default=1, verbose_name="Количество")),
                        ("price_at_moment", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Цена на момент заказа")),
                        ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="orders.order")),
                        ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="main.product", verbose_name="Товар")),
                    ],
                    options={
                        "verbose_name": "Позиция заказа",
                        "verbose_name_plural": "Позиции заказа",
                        "db_table": "order_items",
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
