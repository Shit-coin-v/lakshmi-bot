from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0025_alter_transaction_receipt_line"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["customer", "-created_at"],
                name="order_customer_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(
                fields=["customer"],
                name="transaction_customer_idx",
            ),
        ),
    ]
