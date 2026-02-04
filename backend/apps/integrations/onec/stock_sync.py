import json

from django.http import JsonResponse

from apps.integrations.onec.serializers import StockUpdateSerializer
from apps.orders.models import Product


def onec_stock_sync_impl(request):
    raw_body = request.body or b"{}"
    if isinstance(raw_body, (bytes, bytearray)):
        raw_body = raw_body.decode("utf-8")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return JsonResponse({"detail": "invalid_json"}, status=400)

    serializer = StockUpdateSerializer(data=payload)
    if not serializer.is_valid():
        return JsonResponse({"detail": serializer.errors}, status=400)

    items = serializer.validated_data["items"]
    codes = [item["product_code"] for item in items]
    products = {p.product_code: p for p in Product.objects.filter(product_code__in=codes)}

    updated = 0
    not_found = []
    to_update = []

    for item in items:
        product = products.get(item["product_code"])
        if product is None:
            not_found.append(item["product_code"])
            continue
        product.stock = item["stock"]
        to_update.append(product)
        updated += 1

    if to_update:
        Product.objects.bulk_update(to_update, ["stock"])

    return JsonResponse({"updated": updated, "not_found": not_found})
