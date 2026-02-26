"""Django ORM-based broadcast sender with dual-channel support (Push + Telegram)."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

# Category → CustomUser field mapping for filtering
_CATEGORY_FILTER = {
    "promo": {"promo_enabled": True},
    "news": {"news_enabled": True},
    "general": {"general_enabled": True},
}


async def send_with_django(message_id: int, bot_instance: Bot | None = None) -> None:
    """Send broadcast using Django ORM (for use in Celery tasks).

    Recipients are split into two channels:
    - Push: users with a registered FCM token (logged into the Flutter app)
    - Telegram: users without an FCM token
    """

    from .helpers import (
        BATCH_DELAY_SECONDS,
        BATCH_SIZE,
        OPEN_CALLBACK_PREFIX,
        Recipient,
        chunked,
        send_message_with_retry,
        generate_unique_open_token,
        parse_target_user_ids,
    )

    try:
        from asgiref.sync import sync_to_async
        from django.core.exceptions import ObjectDoesNotExist
        from django.db import transaction
        from apps.main.models import (
            BroadcastMessage as DjangoBroadcastMessage,
            CustomUser as DjangoCustomUser,
            CustomerDevice as DjangoCustomerDevice,
            Notification as DjangoNotification,
            NewsletterDelivery as DjangoNewsletterDelivery,
        )
    except Exception as exc:  # pragma: no cover
        logger.error("Unable to import Django models for broadcast: %s", exc)
        raise

    # --- Load message ---

    @sync_to_async(thread_sensitive=True)
    def load_message() -> DjangoBroadcastMessage:
        return DjangoBroadcastMessage.objects.get(pk=message_id)

    try:
        message = await load_message()
    except ObjectDoesNotExist:
        logger.warning("Broadcast message %s not found", message_id)
        return

    # --- Fetch recipients (with category filter) ---

    @sync_to_async(thread_sensitive=True)
    def fetch_recipients() -> List[Recipient]:
        base_qs = DjangoCustomUser.objects.filter(
            telegram_id__isnull=False,
            telegram_id__gt=0,
            newsletter_enabled=True,
        )
        # Apply category filter
        cat_filter = _CATEGORY_FILTER.get(message.category)
        if cat_filter:
            base_qs = base_qs.filter(**cat_filter)

        if not message.send_to_all:
            target_ids = parse_target_user_ids(message.target_user_ids)
            if not target_ids:
                return []
            base_qs = base_qs.filter(telegram_id__in=target_ids)

        return [
            Recipient(customer_id=user.id, telegram_id=user.telegram_id)
            for user in base_qs.order_by("id").only("id", "telegram_id")
        ]

    recipients = await fetch_recipients()
    if not recipients:
        logger.info("Broadcast %s resolved to 0 recipients", message_id)
        return

    # --- Split recipients by channel ---

    @sync_to_async(thread_sensitive=True)
    def split_by_channel(recs: List[Recipient]):
        push_customer_ids = set(
            DjangoCustomerDevice.objects
            .filter(customer_id__in=[r.customer_id for r in recs])
            .exclude(fcm_token__isnull=True)
            .exclude(fcm_token="")
            .values_list("customer_id", flat=True)
            .distinct()
        )
        push_users = [r for r in recs if r.customer_id in push_customer_ids]
        tg_users = [r for r in recs if r.customer_id not in push_customer_ids]
        return push_users, tg_users

    push_users, telegram_users = await split_by_channel(recipients)

    # --- Fetch already-delivered customer IDs ---

    @sync_to_async(thread_sensitive=True)
    def fetch_existing() -> set[int]:
        return set(
            DjangoNewsletterDelivery.objects.filter(message_id=message_id).values_list(
                "customer_id", flat=True
            )
        )

    delivered_customer_ids = await fetch_existing()

    logger.info(
        "Broadcast %s: %s push, %s telegram, %s already delivered",
        message_id,
        len(push_users),
        len(telegram_users),
        len(delivered_customer_ids),
    )

    total_sent = total_skipped = total_errors = 0

    # ================================================================
    # PUSH CHANNEL — create Notification + NewsletterDelivery
    # The post_save signal on Notification fires notify_notification_created()
    # which sends the FCM push automatically.
    # ================================================================

    @sync_to_async(thread_sensitive=True)
    def create_push_delivery(customer_id: int):
        with transaction.atomic():
            if DjangoNewsletterDelivery.objects.filter(
                message_id=message_id, customer_id=customer_id
            ).exists():
                return None
            notif = DjangoNotification.objects.create(
                user_id=customer_id,
                title="Рассылка",
                body=message.message_text,
                type="broadcast",
            )
            return DjangoNewsletterDelivery.objects.create(
                message_id=message_id,
                customer_id=customer_id,
                channel="push",
                notification=notif,
            )

    for batch in chunked(push_users, BATCH_SIZE):
        for recipient in batch:
            if recipient.customer_id in delivered_customer_ids:
                total_skipped += 1
                continue

            try:
                delivery = await create_push_delivery(recipient.customer_id)
            except Exception as exc:  # pragma: no cover
                total_errors += 1
                logger.exception(
                    "Broadcast %s: push error for customer %s: %s",
                    message_id, recipient.customer_id, exc,
                )
                continue

            if delivery is None:
                total_skipped += 1
            else:
                total_sent += 1
                logger.info(
                    "Broadcast %s: push sent to customer %s (delivery %s)",
                    message_id, recipient.customer_id, delivery.id,
                )
            delivered_customer_ids.add(recipient.customer_id)

        if len(batch) == BATCH_SIZE:
            await asyncio.sleep(BATCH_DELAY_SECONDS)

    # ================================================================
    # TELEGRAM CHANNEL — send via bot with spoiler + "Show" button
    # ================================================================

    if not telegram_users or bot_instance is None:
        if telegram_users and bot_instance is None:
            logger.warning(
                "Broadcast %s: %s telegram recipients skipped — no bot token configured",
                message_id, len(telegram_users),
            )
        logger.info(
            "Broadcast %s completed: sent=%s skipped=%s errors=%s",
            message_id, total_sent, total_skipped, total_errors,
        )
        return

    async def token_exists(token: str) -> bool:
        @sync_to_async(thread_sensitive=True)
        def _exists() -> bool:
            return DjangoNewsletterDelivery.objects.filter(open_token=token).exists()
        return await _exists()

    async def create_tg_delivery(
        customer_id: int,
        chat_id: int,
        tg_message_id: int,
        token: str,
    ):
        @sync_to_async(thread_sensitive=True)
        def _create():
            with transaction.atomic():
                if DjangoNewsletterDelivery.objects.filter(
                    message_id=message_id, customer_id=customer_id
                ).exists():
                    return None
                return DjangoNewsletterDelivery.objects.create(
                    message_id=message_id,
                    customer_id=customer_id,
                    chat_id=chat_id,
                    telegram_message_id=tg_message_id,
                    open_token=token,
                    channel="telegram",
                )
        return await _create()

    async with bot_instance:
        for batch in chunked(telegram_users, BATCH_SIZE):
            for recipient in batch:
                if recipient.customer_id in delivered_customer_ids:
                    total_skipped += 1
                    continue

                token = await generate_unique_open_token(token_exists)
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Показать",
                                callback_data=f"{OPEN_CALLBACK_PREFIX}{token}",
                            )
                        ]
                    ]
                )
                spoiler_text = f"<tg-spoiler>{message.message_text}</tg-spoiler>"

                try:
                    sent_message = await send_message_with_retry(
                        bot_instance,
                        recipient.telegram_id,
                        spoiler_text,
                        keyboard,
                    )
                except TelegramForbiddenError:
                    total_errors += 1
                    continue
                except Exception as exc:  # pragma: no cover
                    total_errors += 1
                    logger.exception(
                        "Unexpected error sending to %s: %s",
                        recipient.telegram_id, exc,
                    )
                    continue

                delivery = await create_tg_delivery(
                    recipient.customer_id,
                    sent_message.chat.id,
                    sent_message.message_id,
                    token,
                )

                if delivery is None:
                    total_skipped += 1
                    delivered_customer_ids.add(recipient.customer_id)
                    continue

                delivered_customer_ids.add(recipient.customer_id)
                total_sent += 1
                logger.info(
                    "Broadcast %s: telegram sent to %s (delivery %s)",
                    message_id, recipient.telegram_id, delivery.id,
                )

            if len(batch) == BATCH_SIZE:
                await asyncio.sleep(BATCH_DELAY_SECONDS)

    logger.info(
        "Broadcast %s completed: sent=%s skipped=%s errors=%s",
        message_id, total_sent, total_skipped, total_errors,
    )
