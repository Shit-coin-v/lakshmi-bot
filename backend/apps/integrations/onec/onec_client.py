"""Shared HTTP client for outbound 1C integration calls."""
from __future__ import annotations

import base64
import logging
import os
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def get_onec_bonus_url() -> str | None:
    """Return 1C bonus URL or None if not configured."""
    url = getattr(settings, "ONEC_BONUS_URL", "") or ""
    if not url or url.startswith("CHANGE_ME"):
        return None
    return url


def build_onec_headers() -> dict[str, str]:
    """Build standard headers for outbound 1C requests (X-Api-Key + optional Basic Auth)."""
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": os.getenv("INTEGRATION_API_KEY", ""),
    }
    onec_user = os.getenv("ONEC_BASIC_AUTH_USER", "")
    if onec_user:
        onec_pass = os.getenv("ONEC_BASIC_AUTH_PASSWORD", "")
        credentials = base64.b64encode(
            f"{onec_user}:{onec_pass}".encode("utf-8")
        ).decode("ascii")
        headers["Authorization"] = f"Basic {credentials}"
    return headers


def send_bonus_to_onec(
    card_id: str, bonus_amount: Decimal, is_accrual: bool, receipt_guid: str,
) -> dict:
    """Send bonus accrual/deduction command to 1C. Raises on error.

    Payload format:
    {
        "card_id": "LC-000042",
        "bonus_amount": "100.00",
        "is_accrual": true,
        "receipt_guid": "abc-123"
    }
    """
    url = get_onec_bonus_url()
    if not url:
        raise ValueError("ONEC_BONUS_URL not configured")

    payload = {
        "card_id": card_id,
        "bonus_amount": str(bonus_amount),
        "is_accrual": is_accrual,
        "receipt_guid": receipt_guid,
    }
    headers = build_onec_headers()

    logger.info(
        "send_bonus_to_onec: card_id=%s bonus=%s accrual=%s receipt=%s url=%s",
        card_id, bonus_amount, is_accrual, receipt_guid, url,
    )

    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")

    result = {"status": "ok", "http_status": resp.status_code}
    try:
        body = resp.json()
        if "new_balance" in body:
            result["new_balance"] = body["new_balance"]
    except (ValueError, KeyError):
        pass
    return result
