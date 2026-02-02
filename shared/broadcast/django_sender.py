"""Django ORM-based broadcast sender."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


async def send_with_django(message_id: int, bot_instance: Bot) -> None:
    """Send broadcast using Django ORM (for use in Celery tasks)."""

    # Import helper functions from shared module
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
            NewsletterDelivery as DjangoNewsletterDelivery,
        )
    except Exception as exc:  # pragma: no cover - should not happen in Django context
        logger.error("Unable to import Django models for broadcast: %s", exc)
        raise

    @sync_to_async(thread_sensitive=True)
    def load_message() -> DjangoBroadcastMessage:
        return DjangoBroadcastMessage.objects.get(pk=message_id)

    try:
        message = await load_message()
    except ObjectDoesNotExist:
        logger.warning("Broadcast message %s not found", message_id)
        return

    @sync_to_async(thread_sensitive=True)
    def fetch_recipients() -> List[Recipient]:
        base_qs = DjangoCustomUser.objects.filter(telegram_id__isnull=False, telegram_id__gt=0)
        if message.send_to_all:
            qs = base_qs
        else:
            target_ids = parse_target_user_ids(message.target_user_ids)
            if not target_ids:
                return []
            qs = base_qs.filter(telegram_id__in=target_ids)
        return [
            Recipient(customer_id=user.id, telegram_id=user.telegram_id)
            for user in qs.order_by("id").only("id", "telegram_id")
        ]

    recipients = await fetch_recipients()
    if not recipients:
        logger.info("Broadcast %s resolved to 0 recipients", message_id)
        return

    @sync_to_async(thread_sensitive=True)
    def fetch_existing() -> set[int]:
        return set(
            DjangoNewsletterDelivery.objects.filter(message_id=message_id).values_list(
                "customer_id", flat=True
            )
        )

    delivered_customer_ids = await fetch_existing()

    logger.info(
        "Broadcast %s: sending to %s recipients (already delivered: %s)",
        message_id,
        len(recipients),
        len(delivered_customer_ids),
    )

    total_sent = total_skipped = total_errors = 0

    async def token_exists(token: str) -> bool:
        @sync_to_async(thread_sensitive=True)
        def _exists() -> bool:
            return DjangoNewsletterDelivery.objects.filter(open_token=token).exists()

        return await _exists()

    async def create_delivery(
        customer_id: int,
        chat_id: int,
        telegram_message_id: int,
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
                    telegram_message_id=telegram_message_id,
                    open_token=token,
                )

        return await _create()

    async with bot_instance:
        for batch in chunked(recipients, BATCH_SIZE):
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
                except Exception as exc:  # pragma: no cover - defensive
                    total_errors += 1
                    logger.exception("Unexpected error sending to %s: %s", recipient.telegram_id, exc)
                    continue

                delivery = await create_delivery(
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
                    "Broadcast %s: sent to %s (delivery id %s)",
                    message_id,
                    recipient.telegram_id,
                    delivery.id,
                )

            if len(batch) == BATCH_SIZE:
                await asyncio.sleep(BATCH_DELAY_SECONDS)

    logger.info(
        "Broadcast %s completed: sent=%s skipped=%s errors=%s",
        message_id,
        total_sent,
        total_skipped,
        total_errors,
    )
