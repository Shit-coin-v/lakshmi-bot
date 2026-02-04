"""Generic async HTTP client for 1C API endpoints.

All parameters (url, api_key) are passed explicitly — no dependency on
bot config or Django settings, so this module can be used from both
the backend and bots.
"""

import json
import logging
import uuid
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


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
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
        "X-Idempotency-Key": idempotency_key or str(uuid.uuid4()),
    }

    try:
        async with aiohttp.ClientSession() as client:
            async with client.post(url, data=body, headers=headers) as resp:
                text = await resp.text()
                if resp.status == 200:
                    try:
                        return json.loads(text)
                    except Exception:
                        logger.error("1C: invalid JSON response: %s", text)
                        return None
                else:
                    logger.error("1C request failed (HTTP %s): %s", resp.status, text)
                    return None
    except Exception:
        logger.exception("Failed to reach 1C endpoint %s", url)
        return None
