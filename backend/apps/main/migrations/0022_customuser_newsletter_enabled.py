from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0021_notificationopenevent'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='newsletter_enabled',
            field=models.BooleanField(default=True, verbose_name='Подписка на рассылки'),
        ),
    ]
