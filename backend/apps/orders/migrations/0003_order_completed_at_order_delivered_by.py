from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_alter_order_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='completed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Время завершения'),
        ),
        migrations.AddField(
            model_name='order',
            name='delivered_by',
            field=models.BigIntegerField(blank=True, db_index=True, null=True, verbose_name='Telegram ID курьера'),
        ),
    ]
