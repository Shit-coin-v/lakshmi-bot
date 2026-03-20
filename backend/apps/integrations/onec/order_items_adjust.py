"""1C endpoint: adjust order items (decrease quantity / remove)."""
from __future__ import annotations

import json
import logging

from django.db import transaction as db_tx
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.api.security import require_onec_auth
from apps.integrations.onec.utils import onec_error

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
@require_onec_auth
def onec_order_items_adjust(request):
    from apps.orders.models import Order
    from apps.orders.services import (
        CannotRemoveAllItems,
        DuplicateProductCode,
        InvalidItemPayload,
        InvalidItemQuantity,
        ItemNotFound,
        OrderNotInAssembly,
        adjust_order_items,
    )

    raw = request.body or b"{}"
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return onec_error("invalid_json", "Request body must be valid JSON.")

    order_id = payload.get("order_id")
    if not order_id or isinstance(order_id, bool):
        return onec_error(
            "missing_field",
            "order_id is required.",
            details={"order_id": ["required"]},
        )

    items = payload.get("items")
    if not items or not isinstance(items, list):
        return onec_error(
            "missing_field",
            "items is required and must be a non-empty list.",
            details={"items": ["required, non-empty list"]},
        )

    try:
        with db_tx.atomic():
            result = adjust_order_items(
                order_id=int(order_id),
                items=items,
            )
    except Order.DoesNotExist:
        return onec_error(
            "order_not_found",
            "Order not found.",
            details={"order_id": order_id},
            status_code=404,
        )
    except OrderNotInAssembly as exc:
        return onec_error(
            "invalid_status",
            f"Order is in '{exc.current_status}', expected 'assembly'.",
            details={"current_status": exc.current_status, "required": "assembly"},
            status_code=409,
        )
    except ItemNotFound as exc:
        return onec_error(
            "item_not_found",
            f"Product {exc.product_code} not found in order.",
            details={"product_code": exc.product_code},
        )
    except InvalidItemQuantity as exc:
        return onec_error(
            "invalid_quantity",
            f"Invalid quantity for {exc.product_code}.",
            details={
                "product_code": exc.product_code,
                "current": exc.current,
                "requested": exc.requested,
            },
        )
    except DuplicateProductCode as exc:
        return onec_error(
            "duplicate_product_code",
            f"Duplicate product_code in request: {exc.product_code}.",
            details={"product_code": exc.product_code},
        )
    except CannotRemoveAllItems:
        return onec_error(
            "cannot_remove_all",
            "Cannot remove all items. Use order cancel instead.",
        )
    except InvalidItemPayload as exc:
        return onec_error(
            "invalid_payload",
            str(exc),
            details={"index": exc.index, "reason": exc.reason},
        )
    except (TypeError, ValueError):
        return onec_error(
            "invalid_order_id",
            "order_id must be an integer.",
            details={"order_id": order_id},
        )

    logger.info(
        "Order %s items adjusted: batch_id=%s, changes=%d",
        order_id, result["batch_id"], len(result["changes"]),
    )

    return JsonResponse(
        {
            "status": "ok",
            "order_id": result["order_id"],
            "batch_id": result["batch_id"],
            "products_price": result["products_price"],
            "delivery_price": result["delivery_price"],
            "total_price": result["total_price"],
            "changes": result["changes"],
        },
        status=200,
    )
