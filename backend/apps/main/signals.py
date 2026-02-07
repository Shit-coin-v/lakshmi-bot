import logging

from django.db.models.signals import post_init, post_save
from django.dispatch import receiver

from .models import Order, Notification
from apps.notifications.push import (
    notify_order_status_change,
    notify_notification_created,
)


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
        notify_order_status_change(instance, previous_status=previous)

    instance._previous_status = instance.status


@receiver(post_save, sender=Notification)
def notification_send_push(sender, instance: Notification, created: bool, **kwargs):
    if not created:
        return
    if getattr(instance, "_skip_push", False):
        return

    data_payload = {
        "notification_id": str(instance.id),
        "type": str(instance.type or "personal"),
    }

    try:
        result = notify_notification_created(instance)
        logger.info(
            "Push sent for notification id=%s payload=%s result=%s",
            instance.id,
            data_payload,
            {k: result.get(k) for k in ("sent", "success", "failure")},
        )
    except Exception:  # pragma: no cover — defensive: push failure must not crash signal
        logger.exception("Push send failed for notification id=%s", instance.id)
