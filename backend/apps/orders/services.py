"""Core order business logic.

- Status transitions: used by /onec/order/status and /api/bot/orders/<id>/update-status/.
- Item adjustments: used by /onec/order/items/adjust (1C).
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from django.db import transaction as db_tx
from django.utils import timezone as dj_tz


def get_delivery_zones() -> list[dict]:
    """Список активных зон доставки с ценами из Product.

    Зоны без валидного активного Product не включаются.
    """
    from apps.main.models import Product
    from apps.orders.models import DeliveryZone

    zones = DeliveryZone.objects.filter(is_active=True)
    codes = [z.product_code for z in zones]

    prices = dict(
        Product.objects
        .filter(product_code__in=codes, is_active=True, price__isnull=False)
        .values_list("product_code", "price")
    )

    result = []
    for z in zones:
        price = prices.get(z.product_code)
        if price is None:
            continue
        result.append({
            "name": z.name,
            "product_code": z.product_code,
            "price": str(price),
            "is_default": z.is_default,
        })
    return result

logger = logging.getLogger(__name__)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "new": {"accepted", "canceled"},
    "accepted": {"assembly", "canceled", "new"},
    "assembly": {"ready", "canceled"},
    "ready": {"delivery", "completed", "canceled"},  # completed for pickup
    "delivery": {"arrived", "canceled"},
    "arrived": {"completed", "canceled"},
    "completed": set(),
    "canceled": {"new"},  # reopen
}

VALID_STATUSES = frozenset(ALLOWED_TRANSITIONS.keys())


class InvalidTransition(Exception):
    def __init__(self, current: str, target: str, order_id: int):
        self.current = current
        self.target = target
        self.order_id = order_id
        super().__init__(f"Transition {current} → {target} not allowed for order {order_id}")


class AlreadyAccepted(Exception):
    def __init__(self, order_id: int, assembled_by: int):
        self.order_id = order_id
        self.assembled_by = assembled_by
        super().__init__(f"Order {order_id} already accepted by assembler {assembled_by}")


# --- adjust_order_items exceptions ---

class OrderNotInAssembly(Exception):
    def __init__(self, order_id: int, current_status: str):
        self.order_id = order_id
        self.current_status = current_status
        super().__init__(f"Order {order_id} is in '{current_status}', expected 'assembly'")


class ItemNotFound(Exception):
    def __init__(self, order_id: int, product_code: str):
        self.order_id = order_id
        self.product_code = product_code
        super().__init__(f"Product {product_code} not found in order {order_id}")


class InvalidItemQuantity(Exception):
    def __init__(self, product_code: str, current: int, requested: int):
        self.product_code = product_code
        self.current = current
        self.requested = requested
        super().__init__(f"Invalid quantity for {product_code}: current={current}, requested={requested}")


class DuplicateProductCode(Exception):
    def __init__(self, product_code: str):
        self.product_code = product_code
        super().__init__(f"Duplicate product_code in request: {product_code}")


class CannotRemoveAllItems(Exception):
    def __init__(self, order_id: int):
        self.order_id = order_id
        super().__init__(f"Cannot remove all items from order {order_id}")


class InvalidItemPayload(Exception):
    def __init__(self, index: int, reason: str):
        self.index = index
        self.reason = reason
        super().__init__(f"Invalid item at index {index}: {reason}")


def update_order_status(
    order_id: int,
    new_status: str,
    *,
    assembler_id: int | None = None,
    courier_id: int | None = None,
    cancel_reason: str | None = None,
    canceled_by: str | None = None,
) -> tuple:
    """Transition an order to new_status inside an atomic block.

    Must be called inside ``transaction.atomic()`` by the caller
    (the caller may need to do additional channel-specific updates
    in the same transaction).

    Returns ``(order, previous_status)`` on success.
    Raises ``InvalidTransition`` or ``AlreadyAccepted`` on business-rule violation.
    Raises ``Order.DoesNotExist`` if order not found.
    """
    from .models import Order
    from apps.notifications.tasks import (
        send_order_push_task,
        assign_courier_task,
        redispatch_unassigned_orders,
    )

    o = Order.objects.select_for_update().get(id=order_id)

    previous_status = o.status
    updates: list[str] = []

    if new_status and o.status != new_status:
        allowed_next = ALLOWED_TRANSITIONS.get(o.status, set())
        if new_status not in allowed_next:
            raise InvalidTransition(o.status, new_status, order_id)

        o.status = new_status
        updates.append("status")

        if new_status == "completed":
            o.completed_at = dj_tz.now()
            updates.append("completed_at")
            if courier_id is not None:
                o.delivered_by = int(courier_id)
                updates.append("delivered_by")

        if new_status == "accepted" and assembler_id is not None:
            if o.assembled_by is not None and o.assembled_by != int(assembler_id):
                raise AlreadyAccepted(order_id, o.assembled_by)
            o.assembled_by = int(assembler_id)
            updates.append("assembled_by")

        if new_status == "canceled":
            if canceled_by:
                o.canceled_by = canceled_by
                updates.append("canceled_by")
            if cancel_reason:
                o.cancel_reason = cancel_reason
                updates.append("cancel_reason")

        # Return to pool: clear assembler on reset to new
        if new_status == "new":
            o.assembled_by = None
            updates.append("assembled_by")

    if updates:
        o._skip_signal_notification = True
        o.save(update_fields=updates)

    status_changed = "status" in updates
    if status_changed:
        oid, prev, new = o.id, previous_status, o.status
        payment_status = o.payment_status
        payment_id = o.payment_id
        db_tx.on_commit(lambda: send_order_push_task.delay(oid, prev, new))
        if new == "ready" and o.fulfillment_type != "pickup":
            db_tx.on_commit(lambda: assign_courier_task.delay(oid))
        if new == "completed" and prev in ("delivery", "arrived"):
            db_tx.on_commit(lambda: redispatch_unassigned_orders.delay())
        if new == "completed":
            from apps.integrations.onec.tasks import notify_onec_order_completed
            db_tx.on_commit(lambda: notify_onec_order_completed.delay(oid))
        if new == "completed" and payment_id and payment_status == "authorized":
            from apps.integrations.payments.tasks import capture_payment_task
            db_tx.on_commit(lambda: capture_payment_task.delay(oid))
        if new == "canceled" and payment_id and payment_status in ("authorized", "captured"):
            from apps.integrations.payments.tasks import cancel_payment_task
            db_tx.on_commit(lambda: cancel_payment_task.delay(oid))

    return (o, previous_status)


def adjust_order_items(order_id: int, items: list[dict]) -> dict:
    """Decrease quantities or remove items from an order in assembly.

    Called by 1C when the picker discovers that some products are out of stock.
    Must be called inside ``transaction.atomic()`` by the caller.

    Returns dict with updated prices and list of applied changes.
    Raises domain-specific exceptions on validation failure.
    Raises ``Order.DoesNotExist`` if order not found.
    """
    from .models import Order, OrderItemChange

    # --- pre-validation: structure + duplicates (before DB access) ---
    seen_codes: set[str] = set()
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise InvalidItemPayload(idx, "each item must be an object")

        code = item.get("product_code")
        if not isinstance(code, str) or not code:
            raise InvalidItemPayload(idx, "product_code is required and must be a non-empty string")

        qty = item.get("quantity")
        if isinstance(qty, bool) or not isinstance(qty, int):
            raise InvalidItemPayload(idx, "quantity is required and must be an integer")

        if code in seen_codes:
            raise DuplicateProductCode(code)
        seen_codes.add(code)

    # --- lock order + items ---
    o = Order.objects.select_for_update().get(id=order_id)

    if o.status != "assembly":
        raise OrderNotInAssembly(order_id, o.status)

    order_items = o.items.select_for_update().select_related("product")
    item_map = {oi.product.product_code: oi for oi in order_items}

    # --- validate all items before applying any changes ---
    removals_count = 0
    for item in items:
        code = item["product_code"]
        requested_qty = item["quantity"]

        if code not in item_map:
            raise ItemNotFound(order_id, code)

        current_qty = item_map[code].quantity

        if not isinstance(requested_qty, int) or requested_qty < 0:
            raise InvalidItemQuantity(code, current_qty, requested_qty)

        if requested_qty >= current_qty:
            raise InvalidItemQuantity(code, current_qty, requested_qty)

        if requested_qty == 0:
            removals_count += 1

    # items not mentioned in the request stay untouched
    untouched = len(item_map) - len(items)
    surviving = untouched + (len(items) - removals_count)
    if surviving < 1:
        raise CannotRemoveAllItems(order_id)

    # --- apply changes ---
    batch_id = uuid.uuid4()
    changes = []

    for item in items:
        code = item["product_code"]
        new_qty = item["quantity"]
        oi = item_map[code]
        old_qty = oi.quantity
        change_type = "removed" if new_qty == 0 else "decreased"

        OrderItemChange.objects.create(
            order=o,
            batch_id=batch_id,
            product_code=oi.product.product_code,
            product_name=oi.product.name,
            old_quantity=old_qty,
            new_quantity=new_qty,
            price_at_moment=oi.price_at_moment,
            change_type=change_type,
            source="onec",
        )

        if new_qty == 0:
            oi.delete()
        else:
            oi.quantity = new_qty
            oi.save(update_fields=["quantity"])

        changes.append({
            "product_code": code,
            "action": change_type,
            "old_quantity": old_qty,
            "new_quantity": new_qty,
        })

    # --- recalculate prices ---
    remaining = o.items.all()
    products_price = sum(
        oi.price_at_moment * oi.quantity for oi in remaining
    ) or Decimal("0.00")
    products_price = Decimal(products_price).quantize(Decimal("0.01"))
    total_price = (products_price + o.delivery_price).quantize(Decimal("0.01"))

    o.products_price = products_price
    o.total_price = total_price
    o.save(update_fields=["products_price", "total_price"])

    return {
        "order_id": o.id,
        "batch_id": str(batch_id),
        "products_price": str(o.products_price),
        "delivery_price": str(o.delivery_price),
        "total_price": str(o.total_price),
        "changes": changes,
    }
