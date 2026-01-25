from __future__ import annotations


def notify_order_status_change(order, *, previous_status: str | None = None) -> None:
    from apps.main.push import notify_order_status_change as _notify_order_status_change

    _notify_order_status_change(order, previous_status=previous_status)


def notify_notification_created(notification) -> dict:
    from apps.main.push import notify_notification_created as _notify_notification_created

    return _notify_notification_created(notification)


def send_test_push_to_customer(
    customer_id: int,
    *,
    title: str = "Test",
    body: str = "Hello",
    data: dict | None = None,
    platform: str | None = None,
) -> dict:
    from apps.main.push import send_test_push_to_customer as _send_test_push_to_customer

    return _send_test_push_to_customer(
        customer_id,
        title=title,
        body=body,
        data=data,
        platform=platform,
    )
