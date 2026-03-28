# Generated manually — backfill referral_code for existing users

import random

from django.db import migrations

_REFERRAL_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_REFERRAL_CODE_LENGTH = 8


def _generate_code():
    return "".join(random.choices(_REFERRAL_ALPHABET, k=_REFERRAL_CODE_LENGTH))


def backfill_referral_codes(apps, schema_editor):
    CustomUser = apps.get_model("main", "CustomUser")
    existing_codes = set(
        CustomUser.objects.filter(referral_code__isnull=False)
        .values_list("referral_code", flat=True)
    )
    for user in CustomUser.objects.filter(referral_code__isnull=True).iterator():
        for _attempt in range(20):
            code = _generate_code()
            if code not in existing_codes:
                break
        user.referral_code = code
        user.save(update_fields=["referral_code"])
        existing_codes.add(code)


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0041_customuser_referral_code"),
    ]

    operations = [
        migrations.RunPython(backfill_referral_codes, migrations.RunPython.noop),
    ]
