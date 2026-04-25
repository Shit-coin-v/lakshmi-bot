from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0045_alter_referrer_fk_to_pk"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="hide_from_app",
            field=models.BooleanField(
                default=False,
                db_index=True,
                verbose_name="Скрыть из приложения",
            ),
        ),
    ]
