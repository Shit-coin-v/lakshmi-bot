"""Restore NewsletterDelivery.notification FK pointing to notifications.Notification.

State-only migration: no SQL executed.
Step 3 of 3.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0031_break_fk_and_move_notif"),
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="newsletterdelivery",
                    name="notification",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="newsletter_deliveries",
                        to="notifications.notification",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
