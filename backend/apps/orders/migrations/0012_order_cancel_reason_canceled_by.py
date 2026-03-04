from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0011_order_order_products_price_non_negative_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="cancel_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("client_refused", "Клиент отказался"),
                    ("client_absent", "Клиент отсутствует"),
                    ("damaged", "Товар повреждён"),
                    ("other", "Другая причина"),
                ],
                max_length=20,
                null=True,
                verbose_name="Причина отмены",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="canceled_by",
            field=models.CharField(
                blank=True,
                choices=[
                    ("client", "Клиент"),
                    ("courier", "Курьер"),
                    ("picker", "Сборщик"),
                    ("admin", "Администратор"),
                    ("onec", "1С"),
                ],
                max_length=20,
                null=True,
                verbose_name="Кто отменил",
            ),
        ),
    ]
