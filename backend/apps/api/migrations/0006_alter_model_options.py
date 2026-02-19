from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_alter_onecclientmap_user'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='onecclientmap',
            options={
                'verbose_name': '1С маппинг клиента',
                'verbose_name_plural': '1С маппинги клиентов',
            },
        ),
        migrations.AlterModelOptions(
            name='receiptdedup',
            options={
                'verbose_name': 'Дедупликация чека',
                'verbose_name_plural': 'Дедупликации чеков',
            },
        ),
    ]
