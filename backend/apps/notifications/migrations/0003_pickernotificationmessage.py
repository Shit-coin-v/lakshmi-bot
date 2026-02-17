from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_couriernotificationmessage"),
    ]

    operations = [
        migrations.CreateModel(
            name="PickerNotificationMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("picker_tg_id", models.BigIntegerField(db_index=True)),
                ("telegram_message_id", models.BigIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "picker_notification_messages",
            },
        ),
    ]
