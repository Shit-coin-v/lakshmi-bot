# Generated manually — create ReferralReward model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("loyalty", "0003_transaction_purchase_type"),
        ("main", "0045_alter_referrer_fk_to_pk"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReferralReward",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bonus_amount", models.DecimalField(decimal_places=2, default=50, max_digits=10)),
                ("receipt_guid", models.CharField(max_length=100, verbose_name="GUID чека-триггера")),
                ("source", models.CharField(
                    choices=[("app", "Приложение"), ("telegram", "Telegram"), ("manual", "Ручное")],
                    max_length=20,
                    verbose_name="Источник связи",
                )),
                ("status", models.CharField(
                    choices=[("pending", "Ожидает отправки"), ("success", "Успешно"), ("failed", "Ошибка")],
                    default="pending",
                    max_length=10,
                )),
                ("last_error", models.TextField(blank=True, default="")),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("referrer", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="referral_rewards_given",
                    to="main.customuser",
                )),
                ("referee", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="referral_reward_received",
                    to="main.customuser",
                )),
            ],
            options={
                "db_table": "referral_rewards",
            },
        ),
        migrations.AddConstraint(
            model_name="referralreward",
            constraint=models.UniqueConstraint(
                fields=["referee"],
                name="one_referral_reward_per_referee",
            ),
        ),
    ]
