"""Set newsletter_enabled=True for all users.

The master newsletter toggle is no longer exposed in the UI.
Category-level toggles (promo_enabled, news_enabled, general_enabled)
are now the only way for users to control broadcast preferences.
"""

from django.db import migrations


def set_newsletter_true(apps, schema_editor):
    CustomUser = apps.get_model("main", "CustomUser")
    CustomUser.objects.filter(newsletter_enabled=False).update(newsletter_enabled=True)


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0023_broadcast_dual_channel"),
    ]

    operations = [
        migrations.RunPython(set_newsletter_true, migrations.RunPython.noop),
    ]
