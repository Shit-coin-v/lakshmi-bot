"""Shared broadcast helpers for backend and bots."""

from __future__ import annotations

import asyncio
import logging
import secrets
from dataclasses import dataclass
from typing import Awaitable, Callable, Iterable, List, Sequence

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)

logger = logging.getLogger(__name__)

# Constants
OPEN_CALLBACK_PREFIX = "open:"
BATCH_SIZE = 100
BATCH_DELAY_SECONDS = 1.0


@dataclass(frozen=True)
class Recipient:
    """Lightweight representation of a broadcast recipient."""

    customer_id: int
    telegram_id: int


async def generate_unique_open_token(
    token_exists: Callable[[str], Awaitable[bool]], *, max_attempts: int = 10
) -> str:
    """Generate a unique token for newsletter open tracking."""
    for attempt in range(max_attempts):
        token = secrets.token_hex(16)
        if not await token_exists(token):
            return token
        logger.debug("Collision on newsletter open token %s (attempt %s)", token, attempt + 1)
    raise RuntimeError("Unable to generate unique open token")


def parse_target_user_ids(raw_value: str | None) -> List[int]:
    """Parse a CSV string into a list of distinct positive Telegram IDs."""

    if not raw_value:
        return []

    result: List[int] = []
    seen = set()
    for chunk in raw_value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            telegram_id = int(chunk)
        except ValueError:
            logger.warning("Skipping invalid telegram id '%s'", chunk)
            continue
        if telegram_id <= 0:
            logger.warning("Skipping non-positive telegram id '%s'", chunk)
            continue
        if telegram_id in seen:
            continue
        seen.add(telegram_id)
        result.append(telegram_id)
    return result


def chunked(sequence: Sequence[Recipient], size: int) -> Iterable[Sequence[Recipient]]:
    """Split sequence into chunks of given size."""
    for index in range(0, len(sequence), size):
        yield sequence[index : index + size]


async def send_message_with_retry(bot_instance: Bot, chat_id: int, text: str, reply_markup):
    """Send message with automatic retry on transient errors."""
    attempts = 0
    while True:
        attempts += 1
        try:
            return await bot_instance.send_message(chat_id, text, reply_markup=reply_markup)
        except TelegramForbiddenError as exc:
            logger.warning("Telegram forbids sending to %s: %s", chat_id, exc)
            raise
        except TelegramRetryAfter as exc:
            logger.warning(
                "Rate limited when sending to %s; retrying in %s seconds (attempt %s)",
                chat_id,
                exc.retry_after,
                attempts,
            )
            await asyncio.sleep(exc.retry_after)
        except (TelegramNetworkError, TelegramAPIError, asyncio.TimeoutError) as exc:
            if attempts >= 3:
                logger.error("Giving up sending to %s after %s attempts: %s", chat_id, attempts, exc)
                raise
            delay = min(5, 2 ** attempts)
            logger.warning(
                "Transient error sending to %s (%s); sleeping %s seconds before retry",
                chat_id,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
