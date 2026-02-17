import logging

from django.db import transaction
from django.db.models.signals import post_init, post_save
from django.dispatch import receiver

from .models import Order
from apps.notifications.tasks import send_order_push_task, notify_couriers_new_order, notify_pickers_new_order

logger = logging.getLogger(__name__)


@receiver(post_init, sender=Order)
def _order_post_init(sender, instance: Order, **kwargs):
    """Запоминаем текущий статус при загрузке из БД (I6: без лишнего SELECT)."""
    instance._previous_status = instance.status if instance.pk else None


@receiver(post_save, sender=Order)
def _order_post_save(sender, instance: Order, **kwargs):
    if getattr(instance, "_skip_signal_notification", False):
        return

    previous = getattr(instance, "_previous_status", None)
    if previous is None:
        return

    if previous != instance.status:
        order_id, prev_status, new_status = instance.id, previous, instance.status
        transaction.on_commit(lambda: send_order_push_task.delay(order_id, prev_status, new_status))
        if new_status == "ready":
            transaction.on_commit(lambda: notify_couriers_new_order.delay(order_id))

    # New order created — notify pickers
    if kwargs.get("created", False) and instance.status == "new":
        oid = instance.id
        transaction.on_commit(lambda: notify_pickers_new_order.delay(oid))

    instance._previous_status = instance.status
