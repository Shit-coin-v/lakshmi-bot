from __future__ import annotations

import asyncio
import logging
import os
from typing import List

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database.models import (
    SessionLocal,
    BroadcastMessage as SqlBroadcastMessage,
    CustomUser,
    NewsletterDelivery,
)

# Import shared helpers
from shared.broadcast import (
    BATCH_DELAY_SECONDS,
    BATCH_SIZE,
    OPEN_CALLBACK_PREFIX,
    Recipient,
    chunked,
    generate_unique_open_token,
    parse_target_user_ids,
    send_message_with_retry,
)

load_dotenv()

logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN не задан в переменных окружения. Рассылка остановлена.")
    raise RuntimeError("BOT_TOKEN is required for broadcast")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def _token_exists_sqlalchemy(session, token: str) -> bool:
    result = await session.execute(
        select(NewsletterDelivery.id).where(NewsletterDelivery.open_token == token)
    )
    return result.scalar_one_or_none() is not None


async def _send_with_sqlalchemy(message_id: int, bot_instance: Bot) -> None:
    async with SessionLocal() as session:
        message = await session.get(SqlBroadcastMessage, message_id)
        if not message:
            logger.warning("Broadcast message %s not found", message_id)
            return

        if message.send_to_all:
            query = select(CustomUser).where(
                CustomUser.telegram_id.isnot(None), CustomUser.telegram_id > 0
            )
        else:
            target_ids = parse_target_user_ids(message.target_user_ids)
            if not target_ids:
                logger.info("Broadcast %s has no valid target ids", message_id)
                return
            query = select(CustomUser).where(
                CustomUser.telegram_id.in_(target_ids),
                CustomUser.telegram_id > 0,
            )

        users_result = await session.execute(query.order_by(CustomUser.id))
        recipients = [Recipient(customer_id=user.id, telegram_id=user.telegram_id) for user in users_result.scalars().all()]

        if not recipients:
            logger.info("Broadcast %s resolved to 0 recipients", message_id)
            return

        existing = await session.execute(
            select(NewsletterDelivery.customer_id).where(NewsletterDelivery.message_id == message_id)
        )
        delivered_customer_ids = set(existing.scalars().all())

        logger.info(
            "Broadcast %s: sending to %s recipients (already delivered: %s)",
            message_id,
            len(recipients),
            len(delivered_customer_ids),
        )

        total_sent = total_skipped = total_errors = 0

        async with bot_instance:
            for batch in chunked(recipients, BATCH_SIZE):
                for recipient in batch:
                    if recipient.customer_id in delivered_customer_ids:
                        total_skipped += 1
                        continue

                    token = await generate_unique_open_token(
                        lambda value: _token_exists_sqlalchemy(session, value)
                    )
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

                    delivery = NewsletterDelivery(
                        message_id=message_id,
                        customer_id=recipient.customer_id,
                        chat_id=sent_message.chat.id,
                        telegram_message_id=sent_message.message_id,
                        open_token=token,
                    )

                    session.add(delivery)
                    try:
                        await session.commit()
                    except IntegrityError:
                        total_skipped += 1
                        await session.rollback()
                        delivered_customer_ids.add(recipient.customer_id)
                        logger.info(
                            "Broadcast %s: delivery already exists for user %s", message_id, recipient.telegram_id
                        )
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


async def _send_with_django(message_id: int, bot_instance: Bot) -> None:
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


async def send_broadcast_message(message_id: int, *, bot_instance: Bot | None = None) -> None:
    """Send a broadcast message to the configured recipients."""

    bot_to_use = bot_instance or bot

    try:
        await _send_with_sqlalchemy(message_id, bot_to_use)
    except RuntimeError as exc:
        if "Database is not configured" not in str(exc):
            raise
        logger.info("Falling back to Django ORM for broadcast %s", message_id)
        await _send_with_django(message_id, bot_to_use)
