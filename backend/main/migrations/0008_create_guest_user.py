from django.conf import settings
from django.db import migrations


def _guest_telegram_id():
    value = getattr(settings, "GUEST_TELEGRAM_ID", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def create_guest_user(apps, schema_editor):
    CustomUser = apps.get_model("main", "CustomUser")
    telegram_id = _guest_telegram_id()

    defaults = {"full_name": "Гость", "qr_code": None}
    CustomUser.objects.update_or_create(
        telegram_id=telegram_id,
        defaults=defaults,
    )


def remove_guest_user(apps, schema_editor):
    CustomUser = apps.get_model("main", "CustomUser")
    telegram_id = _guest_telegram_id()
    CustomUser.objects.filter(telegram_id=telegram_id).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0007_alter_customuser_referrer_alter_transaction_customer"),
    ]

    operations = [
        migrations.RunPython(create_guest_user, remove_guest_user),
    ]
