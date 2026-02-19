from __future__ import annotations

import asyncio
import logging
import random
from typing import Awaitable, Callable

from aiogram import Bot

logger = logging.getLogger(__name__)

_RETRY_DELAYS = [10, 20, 30, 45, 60, 90, 120, 180]
_JITTER_FACTOR = 0.25
_in_flight: dict[int, asyncio.Task] = {}


def is_in_flight(order_id: int) -> bool:
    task = _in_flight.get(order_id)
    if task is None:
        return False
    if task.done():
        return False
    return True


async def retry_status_update(
    *,
    bot: Bot,
    chat_id: int,
    message_id: int,
    order_id: int,
    new_status: str,
    update_fn: Callable[[int, str], Awaitable[bool]],
    on_success: Callable[[Bot, int, int, int, str], Awaitable[None]],
    on_failure: Callable[[Bot, int, int, int, str], Awaitable[None]],
) -> None:
    try:
        total = len(_RETRY_DELAYS)
        for attempt, base_delay in enumerate(_RETRY_DELAYS, start=1):
            result = await update_fn(order_id, new_status)
            if result:
                await on_success(bot, chat_id, message_id, order_id, new_status)
                return

            if attempt < total:
                delay = base_delay + base_delay * _JITTER_FACTOR * random.uniform(-1, 1)
                logger.warning(
                    "Retry %d/%d for order %d->%s, sleeping %.1fs",
                    attempt, total, order_id, new_status, delay,
                )
                await asyncio.sleep(delay)

        logger.error(
            "All %d retries exhausted for order %d->%s", total, order_id, new_status,
        )
        await on_failure(bot, chat_id, message_id, order_id, new_status)

    except asyncio.CancelledError:
        logger.info("Retry cancelled for order %d->%s", order_id, new_status)

    except Exception:
        logger.exception("Unexpected error in retry for order %d->%s", order_id, new_status)
        try:
            await on_failure(bot, chat_id, message_id, order_id, new_status)
        except Exception:
            logger.exception("on_failure itself failed for order %d->%s", order_id, new_status)

    finally:
        _in_flight.pop(order_id, None)


def schedule_retry(
    *,
    bot: Bot,
    chat_id: int,
    message_id: int,
    order_id: int,
    new_status: str,
    update_fn: Callable[[int, str], Awaitable[bool]],
    on_success: Callable[[Bot, int, int, int, str], Awaitable[None]],
    on_failure: Callable[[Bot, int, int, int, str], Awaitable[None]],
) -> asyncio.Task:
    task = asyncio.create_task(
        retry_status_update(
            bot=bot,
            chat_id=chat_id,
            message_id=message_id,
            order_id=order_id,
            new_status=new_status,
            update_fn=update_fn,
            on_success=on_success,
            on_failure=on_failure,
        ),
        name=f"retry-order-{order_id}-{new_status}",
    )
    _in_flight[order_id] = task
    return task
