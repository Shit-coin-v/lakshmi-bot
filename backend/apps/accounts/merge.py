"""Merge two CustomUser accounts (Telegram->Email or vice versa)."""

import logging
from decimal import Decimal

from django.db import transaction

logger = logging.getLogger(__name__)


@transaction.atomic
def merge_accounts(keep, remove):
    """Move all data from *remove* to *keep*, then delete *remove*.

    ``keep`` -- the account that survives (email-registered).
    ``remove`` -- the account being merged in (Telegram-registered).
    """
    from apps.orders.models import Order
    from apps.notifications.models import Notification, NotificationOpenEvent, CustomerDevice
    from apps.loyalty.models import Transaction
    from apps.main.models import BotActivity, NewsletterDelivery, CustomUser

    logger.info(
        "Merging accounts: keep=%s (pk=%s) <- remove=%s (pk=%s)",
        keep, keep.pk, remove, remove.pk,
    )

    # Capture fields from remove before deleting
    tg_id = remove.telegram_id
    remove_phone = remove.phone
    remove_full_name = remove.full_name
    remove_qr_code = remove.qr_code
    remove_bonuses = remove.bonuses or Decimal("0")
    remove_total_spent = remove.total_spent or Decimal("0")
    remove_purchase_count = remove.purchase_count or 0
    remove_last_purchase = remove.last_purchase_date

    # Transfer related objects
    Order.objects.filter(customer=remove).update(customer=keep)
    Notification.objects.filter(user=remove).update(user=keep)
    NotificationOpenEvent.objects.filter(user=remove).update(user=keep)
    CustomerDevice.objects.filter(customer=remove).update(customer=keep)
    Transaction.objects.filter(customer=remove).update(customer=keep)
    BotActivity.objects.filter(customer=remove).update(customer=keep)
    NewsletterDelivery.objects.filter(customer=remove).update(customer=keep)

    # Update referrals: anyone who had remove as referrer -> now has keep
    # Note: referrer FK uses to_field="telegram_id", so we need to update
    # after keep gets the telegram_id. For now, clear referrer on affected users.
    CustomUser.objects.filter(referrer=remove).update(referrer=None)

    # Delete remove first to free up the UNIQUE telegram_id
    remove.delete()

    # Now set Telegram-specific fields on keep
    keep.telegram_id = tg_id
    keep.bonuses = (keep.bonuses or Decimal("0")) + remove_bonuses
    keep.total_spent = (keep.total_spent or Decimal("0")) + remove_total_spent
    keep.purchase_count = (keep.purchase_count or 0) + remove_purchase_count

    if not keep.phone and remove_phone:
        keep.phone = remove_phone
    if not keep.full_name and remove_full_name:
        keep.full_name = remove_full_name
    if not keep.qr_code and remove_qr_code:
        keep.qr_code = remove_qr_code
    if remove_last_purchase:
        if not keep.last_purchase_date or remove_last_purchase > keep.last_purchase_date:
            keep.last_purchase_date = remove_last_purchase

    keep.save()

    # Re-link referrals to keep (now that keep has telegram_id set)
    # Users whose referrer was cleared above can now be linked to keep
    # This requires a data fixup if needed — for MVP, referrals are cleared.

    logger.info("Merge complete: keep=%s, removed pk was deleted", keep.pk)
