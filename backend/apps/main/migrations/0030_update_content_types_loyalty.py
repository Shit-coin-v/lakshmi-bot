"""Update content types after moving Transaction to loyalty app."""
from django.db import migrations


def update_content_types(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="main", model="transaction").update(app_label="loyalty")


def reverse_content_types(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="loyalty", model="transaction").update(app_label="main")


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0029_move_transaction_to_loyalty"),
        ("loyalty", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(update_content_types, reverse_content_types),
    ]
