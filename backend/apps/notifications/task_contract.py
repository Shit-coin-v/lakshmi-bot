from __future__ import annotations


def broadcast_send_task(message_id: int) -> None:
    from apps.main import tasks

    tasks.broadcast_send_task.delay(message_id)
