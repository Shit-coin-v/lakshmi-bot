import json

from django.http import JsonResponse

from apps.integrations.onec.serializers import OneCCategorySyncSerializer
from apps.integrations.onec.utils import onec_error
from apps.main.models import Category


def onec_category_sync_impl(request):
    raw_body = request.body or b"{}"
    if isinstance(raw_body, (bytes, bytearray)):
        raw_body = raw_body.decode("utf-8")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return onec_error("invalid_json", "Request body must be valid JSON.")

    serializer = OneCCategorySyncSerializer(data=payload)
    if not serializer.is_valid():
        return onec_error(
            "validation_error", "Invalid payload.", details=serializer.errors,
        )

    items = serializer.validated_data["categories"]

    created = 0
    updated = 0
    parent_linked = 0
    errors = []

    # Pass 1: create/update without parent
    for item in items:
        ext_id = item["external_id"]
        defaults = {
            "name": item["name"],
            "is_active": item["is_active"],
            "sort_order": item["sort_order"] or 0,
        }
        _, was_created = Category.objects.update_or_create(
            external_id=ext_id, defaults=defaults,
        )
        if was_created:
            created += 1
        else:
            updated += 1

    # Pass 2: link parents
    for item in items:
        parent_ext_id = item.get("parent_external_id")
        if not parent_ext_id:
            Category.objects.filter(external_id=item["external_id"]).update(
                parent=None,
            )
            continue

        try:
            parent = Category.objects.get(external_id=parent_ext_id)
        except Category.DoesNotExist:
            errors.append({
                "external_id": item["external_id"],
                "reason": "parent_not_found",
            })
            continue

        Category.objects.filter(external_id=item["external_id"]).update(
            parent=parent,
        )
        parent_linked += 1

    return JsonResponse({
        "created": created,
        "updated": updated,
        "parent_linked": parent_linked,
        "errors": errors,
    })
