import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .order_sync import send_order_to_onec_impl

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5)
def send_order_to_onec(self, order_id: int):
    """Send order to 1C ERP system."""
    return send_order_to_onec_impl(self, order_id)


@shared_task(bind=True, max_retries=0)
def rollback_stuck_assembly_orders(self):
    """Periodic: rollback orders stuck in 'assembly' without 1C confirmation.

    When 1C fetches pending orders via GET /onec/orders/pending, the endpoint
    sets status='assembly'. If 1C crashes before processing, orders stay in
    'assembly' forever. This task rolls them back to 'new' after a timeout.
    """
    from apps.orders.models import Order

    timeout_minutes = 10
    cutoff = timezone.now() - timedelta(minutes=timeout_minutes)

    stuck_ids = list(
        Order.objects.filter(
            status="assembly",
            assembled_by__isnull=True,
            onec_guid__isnull=True,
            created_at__lt=cutoff,
        ).values_list("id", flat=True)
    )

    if not stuck_ids:
        return

    count = Order.objects.filter(
        id__in=stuck_ids, status="assembly",
    ).update(status="new")

    logger.info(
        "rollback_stuck_assembly_orders: rolled back %d/%d orders to 'new'",
        count, len(stuck_ids),
    )
