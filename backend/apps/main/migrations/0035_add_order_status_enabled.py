from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0034_customuser_email_auth"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="order_status_enabled",
            field=models.BooleanField(default=True, verbose_name="Статусы заказов"),
        ),
    ]
