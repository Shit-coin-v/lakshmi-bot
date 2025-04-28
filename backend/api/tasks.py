from celery import shared_task
import asyncio
from broadcast import send_broadcast_message


@shared_task
def broadcast_message_task(message_id):
    asyncio.run(send_broadcast_message(message_id))
