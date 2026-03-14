import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(time_limit=1800, soft_time_limit=1500)
def calculate_showcase_rankings():
    """Ночной расчёт глобальной витрины."""
    from .services import calculate_global_rankings

    stats = calculate_global_rankings()
    logger.info("Расчёт витрины завершён: %s", stats)
    return stats
