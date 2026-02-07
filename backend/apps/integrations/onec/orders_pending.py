from __future__ import annotations

from datetime import datetime, timezone

from django.db import transaction as db_tx
from django.http import JsonResponse
from django.utils import timezone as dj_tz
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from apps.api.security import require_onec_auth
from apps.integrations.onec.utils import onec_error


@csrf_exempt
@require_GET
@require_onec_auth
def onec_orders_pending(request):
    from apps.orders.models import Order

    after_raw = (request.GET.get("after") or "").strip()
    limit_raw = (request.GET.get("limit") or "50").strip()

    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, 200))

    with db_tx.atomic():
        qs = (
            Order.objects.select_for_update(skip_locked=True)
            .select_related("customer")
            .prefetch_related("items__product")
            .filter(status="new")
            .order_by("created_at")
        )

        if after_raw:
            try:
                dt = datetime.fromisoformat(after_raw.replace("Z", "+00:00"))
                if dj_tz.is_naive(dt):
                    dt = dj_tz.make_aware(dt, timezone=timezone.utc)
                qs = qs.filter(created_at__gt=dt)
            except ValueError:
                return onec_error(
                    "invalid_after",
                    "Query param 'after' must be ISO datetime.",
                    details={"after": after_raw},
                )

        orders = []
        returned_ids = []

        for o in qs[:limit]:
            items = []
            for it in o.items.all():
                p = it.product
                items.append(
                    {
                        "product_code": p.product_code,
                        "name": p.name,
                        "quantity": int(it.quantity),
                        "price": str(it.price_at_moment),
                    }
                )

            orders.append(
                {
                    "order_id": o.id,
                    "created_at": o.created_at.isoformat(),
                    "status": o.status,
                    "payment_method": o.payment_method,
                    "fulfillment_type": o.fulfillment_type,
                    "customer": {
                        "id": o.customer_id,
                        "telegram_id": o.customer.telegram_id,
                        "full_name": o.customer.full_name,
                        "phone": o.phone,
                    },
                    "delivery": {"address": o.address, "comment": o.comment},
                    "prices": {
                        "products_price": str(o.products_price),
                        "delivery_price": str(o.delivery_price),
                        "total_price": str(o.total_price),
                    },
                    "items": items,
                }
            )
            returned_ids.append(o.id)

        if returned_ids:
            Order.objects.filter(id__in=returned_ids, status="new").update(status="assembly")

    return JsonResponse({"status": "ok", "count": len(orders), "orders": orders}, status=200)
