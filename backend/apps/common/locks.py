"""Singleton-локи для Celery beat-задач через Django cache.

Защита от двойного выполнения при overlap расписания или рестарте beat.
В проде backend — django-redis (атомарный SETNX), в тестах — LocMemCache.
"""
from contextlib import contextmanager
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)


@contextmanager
def task_lock(name: str, ttl_seconds: int):
    """Атомарный SETNX-лок на время выполнения задачи.

    Первый вызов получает True; параллельные — False до истечения TTL или release.

        with task_lock("rfm-recalc", ttl_seconds=3600) as acquired:
            if not acquired:
                logger.info("...: lock held, skipping")
                return
            ...
    """
    key = f"task-lock:{name}"
    acquired = cache.add(key, "1", timeout=ttl_seconds)
    try:
        yield acquired
    finally:
        if acquired:
            try:
                cache.delete(key)
            except Exception:
                logger.exception("task_lock release failed: %s", name)
