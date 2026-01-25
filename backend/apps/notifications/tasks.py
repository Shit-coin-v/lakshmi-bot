from __future__ import annotations

from celery import shared_task


@shared_task
def send_birthday_congratulations():
    from apps.api.tasks import send_birthday_congratulations as _legacy_task

    return _legacy_task()
