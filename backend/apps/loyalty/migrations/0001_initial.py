"""Create Transaction in loyalty app (C10 God Model fix).

State-only migration: no SQL executed. Table already exists from main app migrations.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("main", "0029_move_transaction_to_loyalty"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Transaction",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("quantity", models.IntegerField(blank=True, null=True)),
                        ("total_amount", models.DecimalField(decimal_places=2, max_digits=10)),
                        ("bonus_earned", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                        ("purchase_date", models.DateField(blank=True, null=True)),
                        ("purchase_time", models.TimeField(blank=True, null=True)),
                        ("store_id", models.IntegerField()),
                        ("is_promotional", models.BooleanField(blank=True, null=True)),
                        ("price", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                        ("purchased_at", models.DateTimeField(blank=True, null=True)),
                        ("idempotency_key", models.UUIDField(blank=True, null=True, unique=True)),
                        ("receipt_total_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                        ("receipt_discount_total", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                        ("receipt_bonus_spent", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                        ("receipt_bonus_earned", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                        ("receipt_guid", models.CharField(blank=True, max_length=64, null=True)),
                        ("receipt_line", models.IntegerField(blank=True, null=True)),
                        ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="main.customuser")),
                        ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to="main.product")),
                    ],
                    options={
                        "db_table": "transactions",
                    },
                ),
                migrations.AddConstraint(
                    model_name="transaction",
                    constraint=models.UniqueConstraint(fields=("receipt_guid", "receipt_line"), name="uniq_receipt_line"),
                ),
                migrations.AddIndex(
                    model_name="transaction",
                    index=models.Index(fields=["customer"], name="transaction_customer_idx"),
                ),
            ],
            database_operations=[],
        ),
    ]
