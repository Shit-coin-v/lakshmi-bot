from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0009_newsletterdelivery_newsletteropenevent_and_more"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="newsletteropenevent",
            constraint=models.UniqueConstraint(
                fields=("delivery",),
                name="newsletter_open_events_delivery_key",
            ),
        ),
    ]
