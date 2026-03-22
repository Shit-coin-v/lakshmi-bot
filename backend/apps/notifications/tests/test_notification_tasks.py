"""Tests for notifications/tasks.py — Celery tasks for push and Telegram notifications."""

from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.main.models import CustomUser
from apps.notifications.models import Notification
from apps.orders.models import Order


_TEST_SETTINGS = {
    "CACHES": {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    "CELERY_TASK_ALWAYS_EAGER": True,
}


@override_settings(**_TEST_SETTINGS)
class SendOrderPushTaskTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.customer = CustomUser.objects.create(telegram_id=60001)
        self.order = Order.objects.create(
            customer=self.customer, address="test", phone="+7900",
            total_price=100, products_price=100,
        )

    @patch("apps.notifications.push.notify_order_status_change")
    def test_calls_notify(self, mock_notify):
        from apps.notifications.tasks import send_order_push_task
        send_order_push_task.apply(args=[self.order.id, "new", "assembly"])

        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args
        self.assertEqual(call_kwargs.kwargs["previous_status"], "new")
        self.assertEqual(call_kwargs.kwargs["new_status"], "assembly")

    @patch("apps.notifications.push.notify_order_status_change")
    def test_dedup_prevents_duplicate_push(self, mock_notify):
        from apps.notifications.tasks import send_order_push_task
        send_order_push_task.apply(args=[self.order.id, "new", "assembly"])
        send_order_push_task.apply(args=[self.order.id, "new", "assembly"])

        # Should be called only once due to cache dedup
        mock_notify.assert_called_once()

    @patch("apps.notifications.push.notify_order_status_change", side_effect=Exception("boom"))
    def test_cache_cleared_on_failure(self, mock_notify):
        from django.core.cache import cache
        from apps.notifications.tasks import send_order_push_task

        # With autoretry_for=(Exception,) in eager mode, Celery retries
        # until max_retries, then raises. Each retry clears the cache.
        result = send_order_push_task.apply(args=[self.order.id, "new", "assembly"])
        # After all retries exhausted, result is a failure
        self.assertTrue(result.failed())

        # Cache should be cleared after final failure so redispatch can proceed
        cache_key = f"push:order:{self.order.id}:new->assembly"
        self.assertIsNone(cache.get(cache_key))


@override_settings(**_TEST_SETTINGS)
class SendPushNotificationTaskTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.customer = CustomUser.objects.create(telegram_id=60010)
        self.notification = Notification.objects.create(
            user=self.customer, title="Test", body="Body",
        )

    @patch("apps.notifications.push.notify_notification_created")
    def test_sends_push(self, mock_push):
        mock_push.return_value = {"sent": 1, "success": 1, "failure": 0}

        from apps.notifications.tasks import send_push_notification_task
        send_push_notification_task.apply(args=[self.notification.id])
        mock_push.assert_called_once()

    @patch("apps.notifications.push.notify_notification_created")
    def test_dedup_prevents_duplicate(self, mock_push):
        mock_push.return_value = {"sent": 1, "success": 1, "failure": 0}

        from apps.notifications.tasks import send_push_notification_task
        send_push_notification_task.apply(args=[self.notification.id])
        send_push_notification_task.apply(args=[self.notification.id])
        mock_push.assert_called_once()

    @patch("apps.notifications.push.notify_notification_created")
    def test_firebase_not_configured_handled(self, mock_push):
        from django.core.exceptions import ImproperlyConfigured
        mock_push.side_effect = ImproperlyConfigured("no firebase")

        from apps.notifications.tasks import send_push_notification_task
        # Should not raise
        send_push_notification_task.apply(args=[self.notification.id])


@override_settings(**_TEST_SETTINGS, TELEGRAM_BOT_TOKEN="test-bot-token")
class SendBirthdayCongratulationsTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        today = date.today()
        self.birthday_user = CustomUser.objects.create(
            telegram_id=60020, full_name="Birthday Person",
            birth_date=today.replace(year=1990),
        )

    @patch("apps.notifications.tasks.requests.post")
    def test_sends_birthday_message(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        from apps.notifications.tasks import send_birthday_congratulations
        send_birthday_congratulations.apply()

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(payload["chat_id"], 60020)
        self.assertIn("Birthday Person", payload["text"])

    @override_settings(TELEGRAM_BOT_TOKEN="")
    def test_skips_when_no_bot_token(self):
        from apps.notifications.tasks import send_birthday_congratulations
        # Should not raise
        send_birthday_congratulations.apply()

    @patch("apps.notifications.tasks.requests.post")
    def test_no_birthday_users_sends_nothing(self, mock_post):
        self.birthday_user.birth_date = date(1990, 1, 1)  # Not today
        self.birthday_user.save(update_fields=["birth_date"])

        from apps.notifications.tasks import send_birthday_congratulations
        send_birthday_congratulations.apply()
        mock_post.assert_not_called()
