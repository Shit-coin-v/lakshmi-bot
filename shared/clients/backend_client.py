"""Async HTTP client for Django bot_api endpoints.

All parameters (base_url, api_key) are passed explicitly so this module
can be used from both customer_bot and courier_bot.
"""

import asyncio
import json
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=10)
_MAX_RETRIES = 3


class BackendClient:
    """HTTP client for /api/bot/* endpoints."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=_TIMEOUT)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key,
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_data: dict | None = None,
        params: dict | None = None,
    ) -> dict | list | None:
        """Execute HTTP request with retry.  Returns parsed JSON or None."""
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None
        session = await self._get_session()

        for attempt in range(_MAX_RETRIES):
            try:
                kwargs: dict[str, Any] = {"headers": self._headers()}
                if json_data is not None:
                    kwargs["data"] = json.dumps(json_data, ensure_ascii=False)
                if params is not None:
                    kwargs["params"] = params

                async with session.request(method, url, **kwargs) as resp:
                    text = await resp.text()
                    if resp.status in (200, 201):
                        return json.loads(text) if text else {}
                    if resp.status == 204:
                        return {}
                    if resp.status == 404:
                        return None
                    logger.error(
                        "Backend %s %s -> HTTP %s: %s",
                        method, path, resp.status, text,
                    )
                    return None
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_exc = exc
                delay = 2 ** attempt
                logger.warning(
                    "Backend %s %s attempt %d/%d failed: %s, retry in %ds",
                    method, path, attempt + 1, _MAX_RETRIES, exc, delay,
                )
                await asyncio.sleep(delay)
            except Exception:
                logger.exception("Backend request failed: %s %s", method, path)
                return None

        logger.error(
            "Backend %s %s failed after %d attempts: %s",
            method, path, _MAX_RETRIES, last_exc,
        )
        return None

    # --- Generic HTTP methods ---

    async def get(self, path: str, *, params: dict | None = None) -> dict | list | None:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, data: dict) -> dict | list | None:
        return await self._request("POST", path, json_data=data)

    async def patch(self, path: str, data: dict) -> dict | list | None:
        return await self._request("PATCH", path, json_data=data)

    async def delete(self, path: str) -> dict | list | None:
        return await self._request("DELETE", path)

    # --- Domain-specific methods ---

    async def get_user_by_telegram_id(self, telegram_id: int) -> dict | None:
        result = await self.get(f"/api/bot/users/by-telegram-id/{telegram_id}/")
        return result if isinstance(result, dict) else None

    async def register_user(self, data: dict) -> dict | None:
        result = await self.post("/api/bot/users/register/", data)
        return result if isinstance(result, dict) else None

    async def patch_user(self, user_id: int, data: dict) -> dict | None:
        result = await self.patch(f"/api/bot/users/{user_id}/", data)
        return result if isinstance(result, dict) else None

    async def create_activity(self, telegram_id: int, action: str) -> dict | None:
        result = await self.post(
            "/api/bot/activities/",
            {"telegram_id": telegram_id, "action": action},
        )
        return result if isinstance(result, dict) else None

    async def newsletter_open(
        self, token: str, telegram_user_id: int, raw_data: str = "",
    ) -> dict | None:
        result = await self.post("/api/bot/newsletter/open/", {
            "token": token,
            "telegram_user_id": telegram_user_id,
            "raw_callback_data": raw_data,
        })
        return result if isinstance(result, dict) else None

    async def upsert_onec_map(self, user_id: int, one_c_guid: str) -> dict | None:
        result = await self.post("/api/bot/onec-map/upsert/", {
            "user_id": user_id,
            "one_c_guid": one_c_guid,
        })
        return result if isinstance(result, dict) else None

    async def get_active_orders(self, courier_tg_id: int | None = None) -> list[dict]:
        params = {}
        if courier_tg_id is not None:
            params["courier_tg_id"] = str(courier_tg_id)
        result = await self.get("/api/bot/orders/active/", params=params or None)
        return result if isinstance(result, list) else []

    async def get_order_detail(self, order_id: int) -> dict | None:
        result = await self.get(f"/api/bot/orders/{order_id}/detail/")
        return result if isinstance(result, dict) else None

    async def get_completed_today(self, courier_tg_id: int) -> dict | None:
        result = await self.get(
            "/api/bot/orders/completed-today/",
            params={"courier_tg_id": str(courier_tg_id)},
        )
        return result if isinstance(result, dict) else None

    async def get_courier_messages(self, courier_tg_id: int) -> list[dict]:
        result = await self.get(
            "/api/bot/courier-messages/",
            params={"courier_tg_id": str(courier_tg_id)},
        )
        return result if isinstance(result, list) else []

    async def delete_courier_message(self, message_id: int) -> dict | None:
        return await self.delete(f"/api/bot/courier-messages/{message_id}/")

    async def bulk_delete_courier_messages(self, ids: list[int]) -> dict | None:
        result = await self.post("/api/bot/courier-messages/bulk-delete/", {"ids": ids})
        return result if isinstance(result, dict) else None

    # --- Picker Bot ---

    async def get_new_orders(self) -> list[dict]:
        result = await self.get("/api/bot/orders/new/")
        return result if isinstance(result, list) else []

    async def get_picker_active_orders(self, assembler_tg_id: int) -> list[dict]:
        result = await self.get(
            "/api/bot/orders/my-active/",
            params={"assembler_tg_id": str(assembler_tg_id)},
        )
        return result if isinstance(result, list) else []

    async def get_assembled_today(self, assembler_tg_id: int) -> dict | None:
        result = await self.get(
            "/api/bot/orders/assembled-today/",
            params={"assembler_tg_id": str(assembler_tg_id)},
        )
        return result if isinstance(result, dict) else None

    async def get_picker_messages(self, picker_tg_id: int) -> list[dict]:
        result = await self.get(
            "/api/bot/picker-messages/",
            params={"picker_tg_id": str(picker_tg_id)},
        )
        return result if isinstance(result, list) else []

    async def bulk_delete_picker_messages(self, ids: list[int]) -> dict | None:
        result = await self.post("/api/bot/picker-messages/bulk-delete/", {"ids": ids})
        return result if isinstance(result, dict) else None

    # --- Courier Profile ---

    async def get_courier_profile(self, courier_tg_id: int) -> dict | None:
        result = await self.get(
            "/api/bot/courier/profile/",
            params={"courier_tg_id": str(courier_tg_id)},
        )
        return result if isinstance(result, dict) else None

    async def update_order_status(
        self,
        order_id: int,
        new_status: str,
        *,
        courier_id: int | None = None,
        assembler_id: int | None = None,
    ) -> bool:
        """Update order status via /onec/order/status endpoint."""
        payload: dict = {"order_id": order_id, "status": new_status}
        if courier_id is not None:
            payload["courier_id"] = courier_id
        if assembler_id is not None:
            payload["assembler_id"] = assembler_id
        result = await self.post("/onec/order/status", payload)
        return bool(result and isinstance(result, dict) and result.get("status") == "ok")

    async def reassign_order(self, order_id: int) -> bool:
        """POST /api/bot/orders/<id>/reassign/ — transfer order to another courier."""
        result = await self.post(f"/api/bot/orders/{order_id}/reassign/", {})
        return bool(result and isinstance(result, dict) and result.get("status") == "ok")

    async def toggle_accepting(self, courier_tg_id: int, accepting: bool) -> dict | None:
        result = await self.post("/api/bot/courier/toggle-accepting/", {
            "courier_tg_id": courier_tg_id,
            "accepting": accepting,
        })
        return result if isinstance(result, dict) else None

    # --- Staff management ---

    async def check_staff_access(self, telegram_id: int, role: str) -> dict | None:
        """GET /api/bot/staff/check/?telegram_id=X&role=Y
        Returns {"status": "approved"|"pending"|"blacklisted"} or None (404).
        """
        result = await self.get(
            "/api/bot/staff/check/",
            params={"telegram_id": str(telegram_id), "role": role},
        )
        return result if isinstance(result, dict) else None

    async def register_staff(
        self, telegram_id: int, full_name: str, phone: str, role: str,
    ) -> dict | None:
        """POST /api/bot/staff/register/"""
        result = await self.post("/api/bot/staff/register/", {
            "telegram_id": telegram_id,
            "full_name": full_name,
            "phone": phone,
            "role": role,
        })
        return result if isinstance(result, dict) else None
