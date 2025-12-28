from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0010_newsletteropenevent_unique"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="newsletterdelivery",
            constraint=models.UniqueConstraint(
                fields=("message", "customer"),
                name="newsletter_delivery_uc",
            ),
        ),
    ]
