"""Shared access check for staff bots (courier, picker)."""
from __future__ import annotations

from shared.clients.backend_client import BackendClient


async def check_staff_access(backend: BackendClient, telegram_id: int, role: str) -> bool:
    """Check if a staff member is approved via backend API."""
    result = await backend.check_staff_access(telegram_id, role)
    return result is not None and result.get("status") == "approved"
