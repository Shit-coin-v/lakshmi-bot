import logging

from django.db import transaction
from django.db.models.signals import post_init, pre_save, post_save
from django.dispatch import receiver

from .models import Order, CourierProfile, PickerProfile
from apps.notifications.tasks import (
    send_order_push_task,
    assign_courier_task,
    notify_pickers_new_order,
    send_staff_approved_notification,
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

    # New order created — notify pickers (but not SBP orders waiting for payment)
    if kwargs.get("created", False) and instance.status == "new":
        if getattr(instance, "payment_status", "none") != "pending":
            oid = instance.id
            transaction.on_commit(lambda: notify_pickers_new_order.delay(oid))

    previous = getattr(instance, "_previous_status", None)
    if previous is None:
        instance._previous_status = instance.status
        return

    if previous != instance.status:
        order_id, prev_status, new_status = instance.id, previous, instance.status
        transaction.on_commit(lambda: send_order_push_task.delay(order_id, prev_status, new_status))
        if new_status == "ready" and instance.fulfillment_type != "pickup":
            transaction.on_commit(lambda: assign_courier_task.delay(order_id))
        if new_status == "completed":
            from apps.integrations.onec.tasks import notify_onec_order_completed
            transaction.on_commit(lambda: notify_onec_order_completed.delay(order_id))

    instance._previous_status = instance.status


# --- Staff approval notifications ---


@receiver(pre_save, sender=CourierProfile)
def _track_courier_approved(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._was_approved = CourierProfile.objects.filter(
                pk=instance.pk,
            ).values_list("is_approved", flat=True).first()
        except Exception:
            # Не глотаем тихо — без лога БД-проблема в pre_save проходит незамеченной.
            logger.exception("Failed to read previous CourierProfile.is_approved for pk=%s", instance.pk)
            instance._was_approved = False
    else:
        instance._was_approved = False


@receiver(post_save, sender=CourierProfile)
def _notify_courier_approved(sender, instance, **kwargs):
    was = getattr(instance, "_was_approved", None)
    if was is False and instance.is_approved and not instance.is_blacklisted:
        tg_id = instance.telegram_id
        transaction.on_commit(
            lambda: send_staff_approved_notification.delay(tg_id, "courier")
        )


@receiver(pre_save, sender=PickerProfile)
def _track_picker_approved(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._was_approved = PickerProfile.objects.filter(
                pk=instance.pk,
            ).values_list("is_approved", flat=True).first()
        except Exception:
            # См. комментарий в _track_courier_approved.
            logger.exception("Failed to read previous PickerProfile.is_approved for pk=%s", instance.pk)
            instance._was_approved = False
    else:
        instance._was_approved = False


@receiver(post_save, sender=PickerProfile)
def _notify_picker_approved(sender, instance, **kwargs):
    was = getattr(instance, "_was_approved", None)
    if was is False and instance.is_approved and not instance.is_blacklisted:
        tg_id = instance.telegram_id
        transaction.on_commit(
            lambda: send_staff_approved_notification.delay(tg_id, "picker")
        )
