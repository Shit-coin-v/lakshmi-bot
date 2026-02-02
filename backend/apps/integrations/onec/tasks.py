from celery import shared_task
from .order_sync import send_order_to_onec_impl


@shared_task(bind=True, max_retries=7, default_retry_delay=10)
def send_order_to_onec(self, order_id: int):
    """Send order to 1C ERP system."""
    return send_order_to_onec_impl(self, order_id)
