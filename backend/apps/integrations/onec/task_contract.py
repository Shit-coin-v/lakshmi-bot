def send_order_to_onec(order_id: int) -> None:
    from apps.integrations.onec.tasks import send_order_to_onec as send_order_to_onec_task

    send_order_to_onec_task.delay(order_id)
