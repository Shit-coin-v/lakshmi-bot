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


@shared_task(time_limit=3600, soft_time_limit=3000)
def calculate_personal_rankings_task():
    """Ночной расчёт персональных rankings."""
    from django.conf import settings as django_settings

    if not getattr(django_settings, "PERSONAL_RANKING_ENABLED", False):
        logger.info("Personal ranking отключён, пропуск.")
        return {"skipped": True}

    from .services import calculate_all_personal_rankings

    stats = calculate_all_personal_rankings()
    logger.info("Персональный расчёт завершён: %s", stats)
    return stats
