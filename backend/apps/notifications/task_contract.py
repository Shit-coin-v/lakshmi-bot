from __future__ import annotations


def broadcast_send_task(message_id: int) -> None:
    from apps.main.tasks import broadcast_send_task as _task

    _task.delay(message_id)
