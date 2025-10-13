import asyncio
import logging

from celery import shared_task
from django.db import close_old_connections

from .models import BroadcastMessage

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def broadcast_send_task(self, message_id: int) -> None:
    """Schedule sending of a broadcast message via the Telegram bot."""

    close_old_connections()
    try:
        BroadcastMessage.objects.get(pk=message_id)
    except BroadcastMessage.DoesNotExist:
        logger.warning("Broadcast message %s not found; skipping", message_id)
        return

    logger.info("Broadcast %s queued for delivery", message_id)

    from src.broadcast import send_broadcast_message  # imported lazily to avoid circular deps

    try:
        asyncio.run(send_broadcast_message(message_id))
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Broadcast %s failed: %s", message_id, exc)
        raise
    else:
        logger.info("Broadcast %s finished", message_id)
