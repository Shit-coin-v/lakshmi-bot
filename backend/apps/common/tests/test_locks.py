"""Тесты singleton-локов для Celery beat-задач."""
from django.core.cache import cache
from django.test import TestCase

from apps.common.locks import task_lock


class TaskLockTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_first_acquires_second_does_not(self):
        with task_lock("t1", ttl_seconds=10) as a:
            self.assertTrue(a)
            with task_lock("t1", ttl_seconds=10) as b:
                self.assertFalse(b)

    def test_release_allows_next_acquire(self):
        with task_lock("t2", ttl_seconds=10) as a:
            self.assertTrue(a)
        with task_lock("t2", ttl_seconds=10) as b:
            self.assertTrue(b)

    def test_different_names_independent(self):
        with task_lock("name-a", ttl_seconds=10) as a:
            with task_lock("name-b", ttl_seconds=10) as b:
                self.assertTrue(a)
                self.assertTrue(b)

    def test_recalculate_all_rfm_skips_when_locked(self):
        cache.set("task-lock:rfm-recalc", "1", timeout=60)
        from apps.rfm.tasks import recalculate_all_rfm

        with self.assertLogs("apps.rfm.tasks", level="INFO") as cm:
            result = recalculate_all_rfm()

        self.assertIsNone(result)
        self.assertTrue(any("lock held, skipping" in m for m in cm.output))
