"""Move Order and OrderItem from main to orders app (C10 God Model fix).

State-only migration: no SQL executed. Tables remain as-is.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0026_order_order_customer_created_idx_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="OrderItem"),
                migrations.DeleteModel(name="Order"),
            ],
            database_operations=[],
        ),
    ]
