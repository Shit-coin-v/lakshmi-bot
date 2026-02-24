from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0004_alter_model_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="is_read",
            field=models.BooleanField(
                db_index=True, default=False, verbose_name="Прочитано"
            ),
        ),
    ]
