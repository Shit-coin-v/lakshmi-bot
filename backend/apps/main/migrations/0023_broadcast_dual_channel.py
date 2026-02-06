import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0022_customuser_newsletter_enabled'),
    ]

    operations = [
        # CustomUser: category preference fields
        migrations.AddField(
            model_name='customuser',
            name='promo_enabled',
            field=models.BooleanField(default=True, verbose_name='Акции и скидки'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='news_enabled',
            field=models.BooleanField(default=True, verbose_name='Новости магазина'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='general_enabled',
            field=models.BooleanField(default=True, verbose_name='Общие уведомления'),
        ),
        # BroadcastMessage: category field
        migrations.AddField(
            model_name='broadcastmessage',
            name='category',
            field=models.CharField(
                choices=[('general', 'Общая'), ('promo', 'Акции и скидки'), ('news', 'Новости магазина')],
                default='general',
                max_length=10,
                verbose_name='Категория',
            ),
        ),
        # NewsletterDelivery: make telegram-specific fields nullable
        migrations.AlterField(
            model_name='newsletterdelivery',
            name='chat_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='newsletterdelivery',
            name='telegram_message_id',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='newsletterdelivery',
            name='open_token',
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True, unique=True),
        ),
        # NewsletterDelivery: channel field
        migrations.AddField(
            model_name='newsletterdelivery',
            name='channel',
            field=models.CharField(
                choices=[('telegram', 'Telegram'), ('push', 'Push')],
                db_index=True,
                default='telegram',
                max_length=10,
                verbose_name='Канал доставки',
            ),
        ),
        # NewsletterDelivery: link to Notification for push analytics
        migrations.AddField(
            model_name='newsletterdelivery',
            name='notification',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='newsletter_deliveries',
                to='main.notification',
            ),
        ),
    ]
