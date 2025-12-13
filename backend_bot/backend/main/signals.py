from __future__ import annotations

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Order
from .push import notify_order_status_change


@receiver(pre_save, sender=Order)
def _order_pre_save(sender, instance: Order, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return

    try:
        previous = Order.objects.get(pk=instance.pk).status
    except Order.DoesNotExist:
        previous = None

    instance._previous_status = previous


@receiver(post_save, sender=Order)
def _order_post_save(sender, instance: Order, **kwargs):
    if getattr(instance, "_skip_signal_notification", False):
        return

    previous = getattr(instance, "_previous_status", None)
    if previous is None:
        return

    notify_order_status_change(instance, previous_status=previous)
