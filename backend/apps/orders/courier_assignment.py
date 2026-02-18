"""Round-robin courier assignment logic.

When an order reaches 'ready' (delivery), this module picks the next
available courier and writes `delivered_by`.

A courier is *available* when:
  1. CourierProfile.accepting_orders is True
  2. telegram_id is in settings.COURIER_ALLOWED_TG_IDS
  3. Has ZERO orders in 'delivery' or 'arrived' status (not on a route)
  4. Has fewer than MAX_READY_ORDERS orders in 'ready' status

Once a courier taps "Забрал заказ" (ready→delivery), they are blocked
from receiving new orders until ALL their orders are completed/canceled.

Round-robin cursor is stored per store_id (from the order's first item).
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Count

from apps.orders.models import CourierProfile, Order, RoundRobinCursor

logger = logging.getLogger(__name__)

# Statuses meaning courier is "on the road" — blocks new assignments entirely
_ON_ROUTE_STATUSES = {"delivery", "arrived"}
# Max orders a courier can hold in 'ready' status before picking up
MAX_READY_ORDERS = 5


def _get_store_id(order: Order) -> int:
    """Extract store_id from order's first item. Falls back to 0."""
    items = list(order.items.all())  # uses prefetch cache if available
    if items and items[0].product:
        return getattr(items[0].product, "store_id", 0) or 0
    return 0


def _get_available_couriers() -> list[int]:
    """Return sorted list of available courier telegram_ids.

    A courier is available when:
    - accepting_orders=True
    - Has 0 orders in delivery/arrived (not on a route)
    - Has < MAX_READY_ORDERS in 'ready' status
    """
    allowed_ids = set(getattr(settings, "COURIER_ALLOWED_TG_IDS", []))
    if not allowed_ids:
        return []

    # Get couriers with accepting_orders=True AND in the allowed list
    accepting = set(
        CourierProfile.objects.filter(
            accepting_orders=True,
            telegram_id__in=allowed_ids,
        ).values_list("telegram_id", flat=True)
    )

    if not accepting:
        return []

    # Exclude couriers who are on the road (have delivery/arrived orders)
    on_route = set(
        Order.objects.filter(
            delivered_by__in=accepting,
            status__in=_ON_ROUTE_STATUSES,
        )
        .values_list("delivered_by", flat=True)
        .distinct()
    )

    candidates = accepting - on_route
    if not candidates:
        return []

    # Exclude couriers who already have MAX_READY_ORDERS in 'ready'
    overloaded = set(
        Order.objects.filter(
            delivered_by__in=candidates,
            status="ready",
        )
        .values("delivered_by")
        .annotate(cnt=Count("id"))
        .filter(cnt__gte=MAX_READY_ORDERS)
        .values_list("delivered_by", flat=True)
    )

    available = sorted(candidates - overloaded)
    return available


def _pick_next(available: list[int], last_tg_id: int | None) -> int:
    """Pick next courier after last_tg_id in the sorted list (round-robin)."""
    if not available:
        raise ValueError("No available couriers")

    if last_tg_id is None:
        return available[0]

    # Find the index of the next courier after last_tg_id
    for i, tg_id in enumerate(available):
        if tg_id > last_tg_id:
            return tg_id

    # Wrap around
    return available[0]


def assign_courier_to_order(order_id: int) -> int | None:
    """Assign a courier to the order via round-robin.

    Returns the assigned courier's telegram_id, or None if no courier
    is available.

    Must be called within a context where the order is ready for assignment:
    - status == 'ready'
    - fulfillment_type == 'delivery'
    - delivered_by is None
    """
    with transaction.atomic():
        try:
            order = (
                Order.objects.select_for_update()
                .prefetch_related("items__product")
                .get(id=order_id)
            )
        except Order.DoesNotExist:
            logger.error("assign_courier: order %s not found", order_id)
            return None

        # Guard: only assign if ready + delivery + unassigned
        if order.status != "ready":
            logger.info("assign_courier: order %s status=%s, skip", order_id, order.status)
            return None
        if order.fulfillment_type != "delivery":
            logger.info("assign_courier: order %s is pickup, skip", order_id)
            return None
        if order.delivered_by is not None:
            logger.info("assign_courier: order %s already assigned to %s", order_id, order.delivered_by)
            return None

        store_id = _get_store_id(order)
        # Lock cursor BEFORE reading available couriers — acts as a mutex per store
        cursor, _ = RoundRobinCursor.objects.select_for_update().get_or_create(
            store_id=store_id,
            defaults={"last_courier_tg_id": None},
        )

        available = _get_available_couriers()
        if not available:
            logger.info("assign_courier: no available couriers for order %s", order_id)
            return None

        chosen = _pick_next(available, cursor.last_courier_tg_id)

        # Assign
        order.delivered_by = chosen
        order._skip_signal_notification = True
        order.save(update_fields=["delivered_by"])

        cursor.last_courier_tg_id = chosen
        cursor.save(update_fields=["last_courier_tg_id"])

        logger.info(
            "assign_courier: order %s → courier %s (store=%s, available=%s)",
            order_id, chosen, store_id, available,
        )
        return chosen


def get_unassigned_ready_orders() -> list[int]:
    """Return IDs of ready delivery orders without an assigned courier."""
    return list(
        Order.objects.filter(
            status="ready",
            fulfillment_type="delivery",
            delivered_by__isnull=True,
        ).values_list("id", flat=True)
    )
