# Generated manually — add referral_code field (nullable)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0040_customuser_card_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="referral_code",
            field=models.CharField(
                verbose_name="Реферальный код",
                max_length=8,
                null=True,
                blank=True,
                db_index=True,
            ),
        ),
    ]
