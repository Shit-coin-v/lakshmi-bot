# Generated manually — make referral_code NOT NULL + UNIQUE

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0042_backfill_referral_codes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customuser",
            name="referral_code",
            field=models.CharField(
                verbose_name="Реферальный код",
                max_length=8,
                unique=True,
                db_index=True,
            ),
        ),
    ]
