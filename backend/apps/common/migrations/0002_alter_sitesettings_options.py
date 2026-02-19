from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='sitesettings',
            options={
                'verbose_name': 'Настройки доставки',
                'verbose_name_plural': 'Настройки доставки',
            },
        ),
    ]
