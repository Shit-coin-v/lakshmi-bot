from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0006_courierprofile_roundrobincursor'),
    ]

    operations = [
        migrations.CreateModel(
            name='PickerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telegram_id', models.BigIntegerField(db_index=True, unique=True, verbose_name='Telegram ID')),
                ('full_name', models.CharField(blank=True, default='', max_length=200, verbose_name='ФИО')),
                ('phone', models.CharField(blank=True, default='', max_length=20, verbose_name='Телефон')),
                ('is_approved', models.BooleanField(default=False, verbose_name='Подтверждён')),
                ('is_blacklisted', models.BooleanField(default=False, verbose_name='Чёрный список')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
            ],
            options={
                'verbose_name': 'Сборщик',
                'verbose_name_plural': 'Сборщики',
                'db_table': 'picker_profiles',
            },
        ),
        migrations.AlterModelOptions(
            name='courierprofile',
            options={'verbose_name': 'Курьер', 'verbose_name_plural': 'Курьеры'},
        ),
        migrations.AddField(
            model_name='courierprofile',
            name='full_name',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='ФИО'),
        ),
        migrations.AddField(
            model_name='courierprofile',
            name='is_approved',
            field=models.BooleanField(default=False, verbose_name='Подтверждён'),
        ),
        migrations.AddField(
            model_name='courierprofile',
            name='is_blacklisted',
            field=models.BooleanField(default=False, verbose_name='Чёрный список'),
        ),
        migrations.AddField(
            model_name='courierprofile',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='Телефон'),
        ),
        migrations.AlterField(
            model_name='courierprofile',
            name='telegram_id',
            field=models.BigIntegerField(db_index=True, unique=True, verbose_name='Telegram ID'),
        ),
    ]
