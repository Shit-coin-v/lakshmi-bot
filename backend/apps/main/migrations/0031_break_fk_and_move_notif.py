"""Break NewsletterDelivery.notification FK and move Notification cluster out of main.

State-only migration: no SQL executed.
Step 1 of 3: temporarily convert FK to IntegerField, then delete models from state.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0030_update_content_types_loyalty"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                # Step 1: break the FK reference so we can safely delete Notification
                migrations.AlterField(
                    model_name="newsletterdelivery",
                    name="notification",
                    field=models.IntegerField(null=True, blank=True),
                ),
                # Step 2: delete in dependency order
                migrations.DeleteModel(name="CustomerDevice"),
                migrations.DeleteModel(name="NotificationOpenEvent"),
                migrations.DeleteModel(name="Notification"),
            ],
            database_operations=[],
        ),
    ]
