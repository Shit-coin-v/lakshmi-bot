"""Move Transaction from main to loyalty app (C10 God Model fix).

State-only migration: no SQL executed.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0028_update_content_types_orders"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="Transaction"),
            ],
            database_operations=[],
        ),
    ]
