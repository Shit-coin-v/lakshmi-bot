"""Shared notification cleanup for staff bots (courier, picker)."""
from __future__ import annotations

import logging

from aiogram import Bot

from shared.clients.backend_client import BackendClient

logger = logging.getLogger(__name__)


async def cleanup_notifications(
    backend: BackendClient, bot: Bot, chat_id: int, telegram_id: int, role: str,
) -> None:
    """Delete tracked notification messages and remove from DB.

    Args:
        role: "courier" or "picker" — determines which API endpoints to use.
    """
    if role == "courier":
        notifications = await backend.get_courier_messages(telegram_id)
    else:
        notifications = await backend.get_picker_messages(telegram_id)

    if not notifications:
        return

    for n in notifications:
        try:
            await bot.delete_message(chat_id, n["telegram_message_id"])
        except Exception:
            # Cleanup: ожидаемые причины — сообщение уже удалено пользователем
            # или старше 48 часов (Telegram API ограничение). При включённом
            # DEBUG-уровне видим traceback, иначе в логах только сам факт.
            logger.debug(
                "Could not delete notification msg %s",
                n.get("telegram_message_id"),
                exc_info=True,
            )

    ids = [n["id"] for n in notifications]
    if role == "courier":
        await backend.bulk_delete_courier_messages(ids)
    else:
        await backend.bulk_delete_picker_messages(ids)
