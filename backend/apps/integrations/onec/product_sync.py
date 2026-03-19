import json
import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)

from apps.integrations.onec.category_resolver import resolve_category
from apps.integrations.onec.serializers import ProductUpdateSerializer
from apps.integrations.onec.utils import onec_error
from apps.orders.models import Product


def onec_product_sync_impl(request):
    raw_body = request.body or b"{}"
    if isinstance(raw_body, (bytes, bytearray)):
        raw_body = raw_body.decode("utf-8")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return onec_error("invalid_json", "Request body must be valid JSON.")

    serializer = ProductUpdateSerializer(data=payload)
    if not serializer.is_valid():
        logger.warning("Product sync validation failed: %s | payload: %s", serializer.errors, payload)
        return onec_error("validation_error", "Invalid payload.", details=serializer.errors)
    data = serializer.validated_data

    defaults = {
        "one_c_guid": data.get("one_c_guid"),
        "name": data["name"],
        "price": data["price"],
        "category_text": data["category"],
        "category": resolve_category(data["category"]),
        "is_promotional": data["is_promotional"],
    }
    if hasattr(Product, "store_id"):
        defaults.setdefault("store_id", 0)

    product, created = Product.objects.update_or_create(
        product_code=data["product_code"], defaults=defaults
    )

    resp = {
        "status": "created" if created else "updated",
        "product": {
            "product_code": product.product_code,
            "one_c_guid": product.one_c_guid,
            "name": product.name,
            "price": float(product.price),
            "category": product.category_text,
            "is_promotional": product.is_promotional,
        },
    }
    return JsonResponse(resp, status=201 if created else 200)
