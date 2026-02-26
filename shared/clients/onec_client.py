"""Async HTTP client for 1C API endpoints (used by bots).

All parameters (url, api_key) are passed explicitly — no dependency on
bot config or Django settings, so this module can be used from both
the backend and bots.

Note (O4): This is the **async** 1C client (aiohttp), designed for use in
aiogram bot handlers where an event loop is already running. The sync
counterpart lives in ``backend/apps/integrations/onec/order_sync.py``
(requests-based, used in Celery tasks with ``self.retry()``).
This split is intentional — different retry strategies and async contexts.
"""

import asyncio
import json
import logging
import uuid
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=10)
_MAX_RETRIES = 3


async def post_to_onec(
    url: str,
    api_key: str,
    payload: dict[str, Any],
    *,
    idempotency_key: str | None = None,
) -> dict[str, Any] | None:
    """Send a JSON POST request to a 1C endpoint.

    Args:
        url: Full URL of the 1C endpoint.
        api_key: Value for the ``X-Api-Key`` header.
        payload: JSON-serialisable dict to send as the request body.
        idempotency_key: Optional idempotency token; a random UUID is
            generated when not provided.

    Returns:
        Parsed JSON response dict on HTTP 200, or ``None`` on error.
    """
    body = json.dumps(payload, ensure_ascii=False)
    idem_key = idempotency_key or str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
        "X-Idempotency-Key": idem_key,
    }

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            async with aiohttp.ClientSession(timeout=_TIMEOUT) as client:
                async with client.post(url, data=body, headers=headers) as resp:
                    text = await resp.text()
                    if resp.status == 200:
                        try:
                            return json.loads(text)
                        except (json.JSONDecodeError, ValueError):
                            logger.error("1C: invalid JSON response: %s", text)
                            return None
                    else:
                        logger.error("1C request failed (HTTP %s): %s", resp.status, text)
                        return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            last_exc = exc
            delay = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(
                "1C request attempt %d/%d failed (%s), retrying in %ds",
                attempt + 1, _MAX_RETRIES, exc, delay,
            )
            await asyncio.sleep(delay)
        except Exception:
            logger.exception("Failed to reach 1C endpoint %s", url)
            return None

    logger.error("1C request failed after %d attempts: %s", _MAX_RETRIES, last_exc)
    return None
