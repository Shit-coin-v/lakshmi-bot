import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification
from apps.notifications.tasks import send_push_notification_task

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Notification)
def notification_send_push(sender, instance: Notification, created: bool, **kwargs):
    if not created:
        return
    if getattr(instance, "_skip_push", False):
        return

    nid = instance.id
    transaction.on_commit(lambda: send_push_notification_task.delay(nid))
    logger.info("Push task enqueued for notification id=%s", nid)
