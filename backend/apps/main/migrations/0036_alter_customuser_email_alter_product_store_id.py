from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0035_add_order_status_enabled"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customuser",
            name="email",
            field=models.EmailField(
                blank=True, db_index=True, max_length=254, null=True, verbose_name="Email"
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="store_id",
            field=models.IntegerField(db_index=True),
        ),
    ]
