from django.db import migrations

ZONES = [
    {"name": "с. Намцы", "product_code": "ЦБ-00073433", "sort_order": 0, "is_default": True},
    {"name": "с. Аппаны", "product_code": "ЦБ-00073441", "sort_order": 1, "is_default": False},
    {"name": "с. Графский-Берег", "product_code": "ЦБ-00073439", "sort_order": 2, "is_default": False},
    {"name": "с. Кыhыл", "product_code": "ЦБ-00073440", "sort_order": 3, "is_default": False},
]


def seed_zones(apps, schema_editor):
    DeliveryZone = apps.get_model("orders", "DeliveryZone")
    for z in ZONES:
        DeliveryZone.objects.update_or_create(
            product_code=z["product_code"],
            defaults={
                "name": z["name"],
                "sort_order": z["sort_order"],
                "is_default": z["is_default"],
                "is_active": True,
            },
        )


def unseed_zones(apps, schema_editor):
    DeliveryZone = apps.get_model("orders", "DeliveryZone")
    codes = [z["product_code"] for z in ZONES]
    DeliveryZone.objects.filter(product_code__in=codes).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0013_delivery_zones"),
    ]

    operations = [
        migrations.RunPython(seed_zones, unseed_zones),
    ]
