from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0005_alter_notification_is_read"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="notificationopenevent",
            name="uniq_notification_open_once",
        ),
        migrations.AddField(
            model_name="notificationopenevent",
            name="time_to_open",
            field=models.DurationField(
                blank=True, null=True, verbose_name="Время до открытия"
            ),
        ),
    ]
