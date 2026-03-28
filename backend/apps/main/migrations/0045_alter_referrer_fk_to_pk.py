# Generated manually — change referrer FK from to_field="telegram_id" to PK

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0044_remap_referrer_to_pk"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customuser",
            name="referrer",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="referrals",
                db_column="referrer_id",
                to="main.CustomUser",
            ),
        ),
    ]
