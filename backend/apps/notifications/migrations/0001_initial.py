"""Create Notification, NotificationOpenEvent, CustomerDevice in notifications app.

State-only migration: no SQL executed. Tables already exist from main app migrations.
Step 2 of 3.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("main", "0031_break_fk_and_move_notif"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Notification",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("title", models.CharField(max_length=200, verbose_name="Заголовок")),
                        ("body", models.TextField(verbose_name="Текст")),
                        ("is_read", models.BooleanField(default=False, verbose_name="Прочитано")),
                        ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Создано")),
                        ("type", models.CharField(choices=[("personal", "Персональное"), ("broadcast", "Массовое")], db_index=True, default="personal", max_length=20, verbose_name="Тип")),
                        ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="main.customuser", verbose_name="Клиент")),
                    ],
                    options={
                        "verbose_name": "Уведомление",
                        "verbose_name_plural": "Уведомления",
                        "db_table": "notifications",
                    },
                ),
                migrations.AddIndex(
                    model_name="notification",
                    index=models.Index(fields=["user", "-created_at"], name="notif_user_created_idx"),
                ),
                migrations.CreateModel(
                    name="NotificationOpenEvent",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("source", models.CharField(choices=[("inapp", "In-app"), ("push", "Push")], db_index=True, default="inapp", max_length=20, verbose_name="Источник")),
                        ("occurred_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Открыто")),
                        ("notification", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="open_events", to="notifications.notification", verbose_name="Уведомление")),
                        ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notification_open_events", to="main.customuser", verbose_name="Клиент")),
                    ],
                    options={
                        "verbose_name": "Открытие уведомления",
                        "verbose_name_plural": "Открытия уведомлений",
                        "db_table": "notification_open_events",
                    },
                ),
                migrations.AddConstraint(
                    model_name="notificationopenevent",
                    constraint=models.UniqueConstraint(fields=("notification",), name="uniq_notification_open_once"),
                ),
                migrations.CreateModel(
                    name="CustomerDevice",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("fcm_token", models.CharField(max_length=255, unique=True, verbose_name="FCM токен")),
                        ("platform", models.CharField(choices=[("android", "Android"), ("ios", "iOS"), ("web", "Web")], default="android", max_length=20, verbose_name="Платформа")),
                        ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                        ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлен")),
                        ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="devices", to="main.customuser", verbose_name="Клиент")),
                    ],
                    options={
                        "verbose_name": "Устройство клиента",
                        "verbose_name_plural": "Устройства клиентов",
                        "db_table": "customer_devices",
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
