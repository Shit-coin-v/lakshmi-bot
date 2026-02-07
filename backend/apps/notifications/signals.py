import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification
from apps.notifications.push import notify_notification_created

logger = logging.getLogger(__name__)


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
