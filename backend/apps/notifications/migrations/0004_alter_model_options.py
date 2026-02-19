from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0003_pickernotificationmessage'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='couriernotificationmessage',
            options={
                'verbose_name': 'Уведомление курьеру',
                'verbose_name_plural': 'Уведомления курьерам',
            },
        ),
        migrations.AlterModelOptions(
            name='pickernotificationmessage',
            options={
                'verbose_name': 'Уведомление сборщику',
                'verbose_name_plural': 'Уведомления сборщикам',
            },
        ),
    ]
