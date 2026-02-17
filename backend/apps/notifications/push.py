from __future__ import annotations

import json
import logging
import os
from typing import Iterable

from django.core.exceptions import ImproperlyConfigured
from .models import Notification as DBNotification

try:  # firebase-admin is optional until configured
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:  # pragma: no cover - handled at runtime
    firebase_admin = None
    credentials = None
    messaging = None

logger = logging.getLogger(__name__)

_STATUS_MESSAGES = {
    "accepted": "Заказ принят",
    "assembly": "Заказ собирается",
    "ready": "Заказ собран, ждёт курьера",
    "delivery": "Курьер забрал ваш заказ и в пути",
    "arrived": "Курьер пришёл и ждёт вас",
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


def _send_to_tokens(
    tokens: Iterable[str],
    *,
    title: str,
    body: str,
    data: dict | None = None,
    app=None,
) -> dict:
    """
    Отправка без multicast, чтобы не дергать /batch (у тебя он дает 404).
    Возвращает счетчики и список невалидных токенов.
    """
    tokens = [t for t in tokens if t]
    if not tokens:
        return {"sent": 0, "success": 0, "failure": 0, "invalid_tokens": []}

    payload = {str(k): str(v) for k, v in (data or {}).items()}

    success = 0
    failure = 0
    invalid_tokens: list[str] = []

    for token in tokens:
        msg = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=payload,
        )
        try:
            messaging.send(msg, app=app)
            success += 1
        except Exception as exc:  # pragma: no cover - network/config/runtime issues
            failure += 1
            code = getattr(exc, "code", "")  # firebase_admin.exceptions.FirebaseError.code
            logger.warning("FCM push failed token=%s code=%s exc=%s", token, code, exc)

            # Чистим мусорные токены, если Firebase говорит что токен умер
            if code == "registration-token-not-registered" or code == "invalid-argument":
                invalid_tokens.append(token)

    return {"sent": len(tokens), "success": success, "failure": failure, "invalid_tokens": invalid_tokens}


def notify_order_status_change(order, *, previous_status: str | None = None, new_status: str | None = None) -> None:
    """Send a push notification if the status actually changed to a tracked value."""

    event_status = new_status or order.status

    if event_status == previous_status:
        return

    message_text = _STATUS_MESSAGES.get(event_status)
    if not message_text:
        return

    # Самовывоз: другой текст для ready
    if event_status == "ready" and getattr(order, "fulfillment_type", "delivery") == "pickup":
        message_text = "Ваш заказ готов, можете забрать"

    customer = getattr(order, "customer", None)
    if customer and not getattr(customer, "order_status_enabled", True):
        return
    
    notif = DBNotification(
        user=order.customer,
        title="Статус заказа",
        body=message_text,
        type="personal",
    )
    notif._skip_push = True  # чтобы сигнал Notification не отправил второй пуш
    notif.save()

    tokens = _order_tokens(order)
    if not tokens:
        return

    try:
        app = _get_app()
    except Exception:  # pragma: no cover - configuration/runtime issues
        logger.exception("Firebase app is not configured; skipping push notification")
        return

    data_payload = {"order_id": str(order.id), "status": event_status}

    try:
        result = _send_to_tokens(
            tokens,
            title="Статус заказа",
            body=message_text,
            data=data_payload,
            app=app,
        )
    except Exception:  # pragma: no cover
        logger.exception("Failed to send FCM message for order %s", order.id)
        return

    invalid_tokens = result.get("invalid_tokens") or []
    if invalid_tokens:
        from .models import CustomerDevice

        CustomerDevice.objects.filter(fcm_token__in=invalid_tokens).delete()
        logger.info("Removed %s invalid FCM tokens", len(invalid_tokens))

    logger.info(
        "Push notification send result for order %s | payload=%s | result=%s",
        order.id,
        data_payload,
        {k: result.get(k) for k in ("sent", "success", "failure")},
    )


def send_test_push_to_customer(
    customer_id: int,
    *,
    title: str = "Test",
    body: str = "Hello",
    data: dict | None = None,
    platform: str | None = None,
) -> dict:
    """
    Send a test push notification to devices of a customer. 🧪📲

    Важно: отправляет ПО ОДНОМУ токену через messaging.send(),
    чтобы не дергать /batch и не ловить 404.
    """
    from .models import CustomerDevice

    tokens_qs = CustomerDevice.objects.filter(customer_id=customer_id)
    if platform:
        tokens_qs = tokens_qs.filter(platform=platform)

    tokens = list(tokens_qs.values_list("fcm_token", flat=True))
    if not tokens:
        return {"sent": 0, "success": 0, "failure": 0, "detail": "no tokens"}

    app = _get_app()

    result = _send_to_tokens(
        tokens,
        title=title,
        body=body,
        data=data,
        app=app,
    )

    invalid_tokens = result.get("invalid_tokens") or []
    if invalid_tokens:
        CustomerDevice.objects.filter(fcm_token__in=invalid_tokens).delete()
        logger.info("Removed %s invalid FCM tokens (test)", len(invalid_tokens))

    return {
        "sent": result.get("sent", 0),
        "success": result.get("success", 0),
        "failure": result.get("failure", 0),
    }


__all__ = ["notify_order_status_change", "send_test_push_to_customer"]


def notify_notification_created(notification) -> dict:
    tokens = list(
        notification.user.devices.exclude(fcm_token__isnull=True)
        .exclude(fcm_token="")
        .values_list("fcm_token", flat=True)
    )
    if not tokens:
        return {"sent": 0, "success": 0, "failure": 0}

    title = notification.title or "Уведомление"
    body = notification.body or ""

    data = {
        "notification_id": str(notification.id),
        "type": str(notification.type or "personal"),
    }

    app = _get_app()
    return _send_to_tokens(tokens=tokens, title=title, body=body, data=data, app=app)
