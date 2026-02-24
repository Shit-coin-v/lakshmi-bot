from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0009_order_manual_check_required"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="payment_status",
            field=models.CharField(
                choices=[
                    ("none", "Нет онлайн-оплаты"),
                    ("pending", "Ожидает оплаты"),
                    ("authorized", "Авторизован (hold)"),
                    ("captured", "Списан"),
                    ("canceled", "Отменён"),
                    ("failed", "Ошибка"),
                ],
                db_index=True,
                default="none",
                max_length=20,
                verbose_name="Статус платежа",
            ),
        ),
    ]
