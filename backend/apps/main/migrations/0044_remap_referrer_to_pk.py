# Generated manually — remap referrer_id from telegram_id values to PK values

from django.db import migrations


def remap_referrer_ids(apps, schema_editor):
    """Replace telegram_id stored in referrer_id with the actual PK of the referrer."""
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE customers
            SET referrer_id = (
                SELECT c2.id
                FROM customers c2
                WHERE c2.telegram_id = customers.referrer_id
            )
            WHERE referrer_id IS NOT NULL
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0043_referral_code_not_null"),
    ]

    operations = [
        migrations.RunPython(remap_referrer_ids, migrations.RunPython.noop),
    ]
