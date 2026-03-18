"""Core order status transition logic.

Used by both /onec/order/status (1C) and /api/bot/orders/<id>/update-status/ (bots).
"""

from __future__ import annotations

import logging

from django.db import transaction as db_tx
from django.utils import timezone as dj_tz

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
