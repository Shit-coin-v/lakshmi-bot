from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0024_set_newsletter_enabled_true"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="receipt_line",
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
