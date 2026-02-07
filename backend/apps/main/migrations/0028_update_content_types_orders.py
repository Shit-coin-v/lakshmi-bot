"""Update content types after moving Order/OrderItem to orders app."""
from django.db import migrations


def update_content_types(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="main", model="order").update(app_label="orders")
    ContentType.objects.filter(app_label="main", model="orderitem").update(app_label="orders")


def reverse_content_types(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="orders", model="order").update(app_label="main")
    ContentType.objects.filter(app_label="orders", model="orderitem").update(app_label="main")


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0027_move_order_to_orders"),
        ("orders", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(update_content_types, reverse_content_types),
    ]
