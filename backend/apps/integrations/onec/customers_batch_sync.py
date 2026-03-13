from __future__ import annotations

import json
import logging
from hashlib import sha256

from django.db import IntegrityError
from django.http import JsonResponse
from django.utils import timezone

from apps.api.models import OneCClientMap
from apps.integrations.onec.serializers import OneCCustomersSyncSerializer
from apps.integrations.onec.utils import onec_error
from apps.main.models import CustomUser

logger = logging.getLogger(__name__)


def onec_customers_batch_sync_impl(request):
    raw_body = request.body or b"{}"
    if isinstance(raw_body, (bytes, bytearray)):
        raw_body = raw_body.decode("utf-8")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return onec_error("invalid_json", "Request body must be valid JSON.")

    serializer = OneCCustomersSyncSerializer(data=payload)
    if not serializer.is_valid():
        return onec_error(
            "validation_error", "Invalid payload.", details=serializer.errors,
        )

    items = serializer.validated_data["customers"]

    # Deduplicate by one_c_guid — last wins
    seen: dict[str, dict] = {}
    for item in items:
        seen[item["one_c_guid"]] = item
    items = list(seen.values())

    # Batch-load existing mappings
    guids = [item["one_c_guid"] for item in items]
    existing_maps = OneCClientMap.objects.filter(
        one_c_guid__in=guids,
    ).select_related("user")
    guid_to_user: dict[str, CustomUser] = {
        m.one_c_guid: m.user for m in existing_maps
    }

    created = 0
    updated = 0
    errors = []

    for item in items:
        guid = item["one_c_guid"]
        try:
            user = guid_to_user.get(guid)
            if user:
                _update_user(user, item)
                updated += 1
            else:
                _create_user_with_map(item)
                created += 1
        except (IntegrityError, Exception) as exc:  # noqa: BLE001
            logger.exception("customers_batch_sync: error for guid=%s", guid)
            errors.append({
                "one_c_guid": guid,
                "reason": "database_error",
                "detail": str(exc)[:200],
            })

    return JsonResponse({
        "created": created,
        "updated": updated,
        "errors": errors,
    })


def _build_defaults(item: dict) -> dict:
    """Build dict of non-empty fields to set on CustomUser."""
    defaults = {}
    if item.get("first_name"):
        defaults["first_name"] = item["first_name"]
    if item.get("last_name"):
        defaults["last_name"] = item["last_name"]
    if item.get("full_name"):
        defaults["full_name"] = item["full_name"]
    if item.get("phone"):
        defaults["phone"] = item["phone"]
    if item["bonuses"] is not None:
        defaults["bonuses"] = item["bonuses"]
    return defaults


def _update_user(user: CustomUser, item: dict) -> None:
    defaults = _build_defaults(item)
    if not defaults:
        return
    for field, value in defaults.items():
        setattr(user, field, value)
    user.save(update_fields=list(defaults.keys()))


def _onec_placeholder_email(one_c_guid: str) -> str:
    """Deterministic placeholder email from 1C GUID.

    Uses SHA-256 hex digest to avoid collisions and unsafe characters.
    """
    digest = sha256(one_c_guid.encode()).hexdigest()[:24]
    return f"onec-{digest}@onec.local"


def _create_user_with_map(item: dict) -> None:
    defaults = _build_defaults(item)
    defaults.setdefault("created_at", timezone.now())
    defaults.setdefault("email", _onec_placeholder_email(item["one_c_guid"]))
    user = CustomUser.objects.create(**defaults)
    OneCClientMap.objects.create(user=user, one_c_guid=item["one_c_guid"])
