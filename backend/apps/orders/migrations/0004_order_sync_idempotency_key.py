from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_order_completed_at_order_delivered_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='sync_idempotency_key',
            field=models.UUIDField(blank=True, null=True, verbose_name='Ключ идемпотентности синхронизации'),
        ),
    ]
