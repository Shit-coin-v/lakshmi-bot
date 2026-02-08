"""Add email authentication fields to CustomUser."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0033_update_content_types_notifications"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="auth_method",
            field=models.CharField(
                choices=[("telegram", "Telegram"), ("email", "Email")],
                default="telegram",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="email_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="customuser",
            name="password_hash",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name="customuser",
            name="telegram_id",
            field=models.BigIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.AddConstraint(
            model_name="customuser",
            constraint=models.CheckConstraint(
                check=models.Q(("telegram_id__isnull", False))
                | models.Q(("email__isnull", False)),
                name="customer_has_telegram_or_email",
            ),
        ),
    ]
