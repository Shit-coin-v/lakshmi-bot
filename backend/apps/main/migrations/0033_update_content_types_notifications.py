"""Update content types after moving Notification cluster to notifications app."""
from django.db import migrations


def update_content_types(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    for model_name in ("notification", "notificationopenevent", "customerdevice"):
        ContentType.objects.filter(app_label="main", model=model_name).update(
            app_label="notifications"
        )


def reverse_content_types(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    for model_name in ("notification", "notificationopenevent", "customerdevice"):
        ContentType.objects.filter(app_label="notifications", model=model_name).update(
            app_label="main"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0032_restore_notification_fk"),
        ("notifications", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(update_content_types, reverse_content_types),
    ]
