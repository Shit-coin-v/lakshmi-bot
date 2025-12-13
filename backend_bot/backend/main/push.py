"""Helpers to send Firebase Cloud Messaging notifications for orders.

Payload example sent to FCM:

```
{
    "notification": {"title": "Статус заказа", "body": "Курьер выехал"},
    "data": {"order_id": "123", "status": "delivery"}
}
```
"""
from __future__ import annotations

import json
import logging
import os
from typing import Iterable

from django.core.exceptions import ImproperlyConfigured

try:  # firebase-admin is optional until configured
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError as exc:  # pragma: no cover - handled at runtime
    firebase_admin = None
    credentials = None
    messaging = None

logger = logging.getLogger(__name__)

_STATUS_MESSAGES = {
    "assembly": "Заказ собирается",
    "delivery": "Курьер выехал",
    "completed": "Заказ доставлен",
    "canceled": "Заказ отменён",
}


def _load_credentials():
    json_blob = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

    if json_blob:
        try:
            data = json.loads(json_blob)
        except json.JSONDecodeError as exc:  # pragma: no cover - config error
            raise ImproperlyConfigured("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON") from exc
        return credentials.Certificate(data)

    if path:
        return credentials.Certificate(path)

    raise ImproperlyConfigured(
        "FIREBASE_SERVICE_ACCOUNT_JSON or FIREBASE_SERVICE_ACCOUNT_PATH must be configured"
    )


_app = None


def _get_app():
    global _app
    if _app is not None:
        return _app

    if firebase_admin is None:
        raise ImproperlyConfigured("firebase-admin is not installed")

    try:
        _app = firebase_admin.get_app()
    except ValueError:
        _app = firebase_admin.initialize_app(_load_credentials())
    return _app


def _order_tokens(order) -> Iterable[str]:
    customer = getattr(order, "customer", None)
    if not customer:
        return []
    return list(customer.devices.values_list("fcm_token", flat=True))


def notify_order_status_change(order, *, previous_status: str | None = None) -> None:
    """Send a push notification if the status actually changed to a tracked value."""

    if order.status == previous_status:
        return

    message_text = _STATUS_MESSAGES.get(order.status)
    if not message_text:
        return

    tokens = _order_tokens(order)
    if not tokens:
        return

    try:
        app = _get_app()
    except Exception:  # pragma: no cover - configuration/runtime issues
        logger.exception("Firebase app is not configured; skipping push notification")
        return

    data_payload = {"order_id": str(order.id), "status": order.status}
    multicast = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title="Статус заказа", body=message_text),
        data=data_payload,
    )

    try:
        response = messaging.send_multicast(multicast, app=app)
    except Exception:  # pragma: no cover - network/config issues
        logger.exception("Failed to send FCM message for order %s", order.id)
        return

    invalid_tokens = []
    for idx, resp in enumerate(response.responses):
        if resp.success:
            continue

        error = resp.exception
        error_code = getattr(error, "code", "")
        logger.warning(
            "FCM push failed for order %s token=%s code=%s", order.id, tokens[idx], error_code
        )

        if error_code == "registration-token-not-registered" or isinstance(
            error, getattr(messaging, "UnregisteredError", ())
        ):
            invalid_tokens.append(tokens[idx])

    if invalid_tokens:
        from .models import CustomerDevice  # imported lazily to avoid circular imports

        CustomerDevice.objects.filter(fcm_token__in=invalid_tokens).delete()
        logger.info("Removed %s invalid FCM tokens", len(invalid_tokens))

    logger.info(
        "Push notification sent for order %s | payload=%s", order.id, data_payload
    )


__all__ = ["notify_order_status_change"]
