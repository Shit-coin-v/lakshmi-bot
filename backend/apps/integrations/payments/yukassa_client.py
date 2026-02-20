"""ЮKassa (YooKassa) HTTP client for payment operations.

Uses the official yookassa SDK.
All methods are synchronous (intended for use in Celery tasks or views).

HTTP-level retry: each API call retries up to 3 times with 1-2s delay
on network/timeout errors before propagating to Celery.
"""

from __future__ import annotations

import logging
import time
import uuid
from decimal import Decimal

from django.conf import settings

logger = logging.getLogger(__name__)

_HTTP_MAX_RETRIES = 2
_HTTP_RETRY_DELAYS = [1, 2]  # seconds, total max ~3s

# HTTP status codes eligible for retry
_RETRYABLE_HTTP_CODES = {429, 502, 503, 504}


class YukassaLogicalError(Exception):
    """Non-retryable logical error from ЮKassa (4xx except 429)."""
    pass


def _configure():
    """Lazy-configure the SDK with shop credentials."""
    from yookassa import Configuration
    if not Configuration.account_id:
        Configuration.account_id = settings.YUKASSA_SHOP_ID
        Configuration.secret_key = settings.YUKASSA_SECRET_KEY


def _extract_status_code(exc: Exception) -> int | None:
    """Try to extract HTTP status code from various exception types."""
    import requests
    # requests.HTTPError
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return exc.response.status_code
    # yookassa SDK may wrap errors with a status_code attribute
    if hasattr(exc, "status_code"):
        return int(exc.status_code)
    # yookassa SDK may include status in args or message
    msg = str(exc)
    for code in (400, 401, 403, 404, 409, 429, 500, 502, 503, 504):
        if str(code) in msg:
            return code
    return None


def _is_retryable_error(exc: Exception) -> bool:
    """Determine if an exception is transient (retryable)."""
    import requests
    # Check HTTP status code first (HTTPError is a subclass of OSError!)
    code = _extract_status_code(exc)
    if code is not None:
        return code in _RETRYABLE_HTTP_CODES
    # Network-level errors without a status code — always retryable
    if isinstance(exc, (requests.ConnectionError, requests.Timeout, OSError)):
        return True
    return False


def _is_logical_error(exc: Exception) -> bool:
    """Determine if an exception is a logical (non-retryable) 4xx error."""
    code = _extract_status_code(exc)
    if code is None:
        return False
    # 4xx except 429 = logical error
    return 400 <= code < 500 and code != 429


def _with_http_retry(fn, *args, **kwargs):
    """Execute fn with HTTP-level retry on transient errors only.

    Retries: timeout, connection error, 502/503/504, 429.
    Does NOT retry logical 4xx (400, 401, 403, 404, 409) — raises YukassaLogicalError.
    Max 2 attempts, total delay ≤ 3s.
    """
    last_exc = None
    for attempt in range(_HTTP_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            if _is_logical_error(exc):
                code = _extract_status_code(exc)
                raise YukassaLogicalError(
                    f"YooKassa logical error (HTTP {code}): {exc}"
                ) from exc

            if _is_retryable_error(exc):
                last_exc = exc
                if attempt < _HTTP_MAX_RETRIES - 1:
                    delay = _HTTP_RETRY_DELAYS[attempt]
                    logger.warning(
                        "YooKassa HTTP retry %d/%d: %s, sleeping %ds",
                        attempt + 1, _HTTP_MAX_RETRIES, exc, delay,
                    )
                    time.sleep(delay)
                continue

            # Unknown error — don't retry at HTTP level, let Celery handle
            raise
    raise last_exc  # type: ignore[misc]


def create_payment(
    *,
    amount: Decimal,
    order_id: int,
    description: str = "",
    return_url: str = "",
) -> dict:
    """Create a payment with hold (capture=false).

    Returns: {"payment_id": str, "confirmation_url": str, "status": str}
    Raises on failure.
    """
    _configure()
    from yookassa import Payment

    idempotency_key = str(uuid.uuid4())
    ret_url = return_url or settings.YUKASSA_RETURN_URL

    params = {
        "amount": {
            "value": str(amount),
            "currency": "RUB",
        },
        "confirmation": {
            "type": "redirect",
            "return_url": ret_url,
        },
        "capture": False,  # hold, not immediate capture
        "description": description or f"Заказ #{order_id}",
        "metadata": {
            "order_id": str(order_id),
        },
        "payment_method_data": {
            "type": "sbp",
        },
    }

    payment = _with_http_retry(Payment.create, params, idempotency_key)

    logger.info(
        "YooKassa payment created: id=%s status=%s order=%s",
        payment.id, payment.status, order_id,
    )

    confirmation_url = ""
    if payment.confirmation:
        confirmation_url = payment.confirmation.confirmation_url or ""

    return {
        "payment_id": payment.id,
        "confirmation_url": confirmation_url,
        "status": payment.status,
    }


def capture_payment(payment_id: str, amount: Decimal | None = None) -> dict:
    """Capture (finalize) an authorized payment.

    Returns: {"payment_id": str, "status": str}
    """
    _configure()
    from yookassa import Payment

    params = {}
    if amount is not None:
        params["amount"] = {
            "value": str(amount),
            "currency": "RUB",
        }

    idempotency_key = str(uuid.uuid4())
    payment = _with_http_retry(Payment.capture, payment_id, params, idempotency_key)

    logger.info("YooKassa capture: id=%s status=%s", payment.id, payment.status)
    return {"payment_id": payment.id, "status": payment.status}


def cancel_payment(payment_id: str) -> dict:
    """Cancel an authorized (held) payment.

    Returns: {"payment_id": str, "status": str}
    """
    _configure()
    from yookassa import Payment

    idempotency_key = str(uuid.uuid4())
    payment = _with_http_retry(Payment.cancel, payment_id, idempotency_key)

    logger.info("YooKassa cancel: id=%s status=%s", payment.id, payment.status)
    return {"payment_id": payment.id, "status": payment.status}


def get_payment(payment_id: str) -> dict:
    """Get payment info.

    Returns: {"payment_id": str, "status": str, "paid": bool}
    """
    _configure()
    from yookassa import Payment

    payment = _with_http_retry(Payment.find_one, payment_id)
    return {
        "payment_id": payment.id,
        "status": payment.status,
        "paid": payment.paid,
    }


def create_refund(payment_id: str, amount: Decimal) -> dict:
    """Create a refund for a captured payment.

    Returns: {"refund_id": str, "status": str}
    """
    _configure()
    from yookassa import Refund

    idempotency_key = str(uuid.uuid4())
    refund = _with_http_retry(
        Refund.create,
        {
            "payment_id": payment_id,
            "amount": {
                "value": str(amount),
                "currency": "RUB",
            },
        },
        idempotency_key,
    )

    logger.info("YooKassa refund: id=%s status=%s", refund.id, refund.status)
    return {"refund_id": refund.id, "status": refund.status}
