import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TransactionTestCase

from apps.main.models import (
    BroadcastMessage,
    CustomUser,
    CustomerDevice,
    NewsletterDelivery,
    Notification,
)
from shared.broadcast.django_sender import send_with_django


class DummyTelegramBot:
    def __init__(self):
        self.sent_messages = []
        self._counter = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send_message(self, chat_id, text, reply_markup=None):
        self._counter += 1
        self.sent_messages.append(
            {
                "chat_id": chat_id,
                "text": text,
                "reply_markup": reply_markup,
            }
        )
        return SimpleNamespace(
            chat=SimpleNamespace(id=chat_id),
            message_id=self._counter,
        )


class BroadcastSendingTests(TransactionTestCase):
    def setUp(self):
        self.bot = DummyTelegramBot()

    def test_send_to_specific_list_creates_deliveries(self):
        user_target = CustomUser.objects.create(telegram_id=200)

        message = BroadcastMessage.objects.create(
            message_text="Secret", send_to_all=False, target_user_ids="200,999"
        )

        asyncio.run(send_with_django(message.id, self.bot))

        deliveries = NewsletterDelivery.objects.filter(message=message).order_by("customer_id")
        self.assertEqual(deliveries.count(), 1)
        self.assertEqual(deliveries[0].customer_id, user_target.id)
        self.assertEqual(self.bot.sent_messages[0]["chat_id"], user_target.telegram_id)
        self.assertTrue(self.bot.sent_messages[0]["text"].startswith("<tg-spoiler>"))
        button = self.bot.sent_messages[0]["reply_markup"].inline_keyboard[0][0]
        self.assertTrue(button.callback_data.startswith("open:"))

    def test_send_to_all_ignores_invalid_ids(self):
        valid_one = CustomUser.objects.create(telegram_id=400)
        valid_two = CustomUser.objects.create(telegram_id=500)
        CustomUser.objects.create(telegram_id=-1)

        message = BroadcastMessage.objects.create(message_text="Promo", send_to_all=True)

        asyncio.run(send_with_django(message.id, self.bot))

        sent_ids = set(
            NewsletterDelivery.objects.filter(message=message).values_list("customer_id", flat=True)
        )
        self.assertSetEqual(sent_ids, {valid_one.id, valid_two.id})

    def test_second_run_does_not_duplicate_deliveries(self):
        user = CustomUser.objects.create(telegram_id=700)
        message = BroadcastMessage.objects.create(message_text="Repeat", send_to_all=True)

        for _ in range(2):
            asyncio.run(send_with_django(message.id, self.bot))

        deliveries = NewsletterDelivery.objects.filter(message=message)
        self.assertEqual(deliveries.count(), 1)
        self.assertEqual(deliveries.first().customer_id, user.id)


class BroadcastDualChannelTests(TransactionTestCase):
    """Tests for dual-channel (push + telegram) broadcast sending."""

    def setUp(self):
        self.bot = DummyTelegramBot()

    @patch("apps.notifications.tasks.send_push_notification_task.delay")
    def test_user_with_fcm_gets_push_not_telegram(self, mock_push):
        mock_push.return_value = {"sent": 1, "success": 1, "failure": 0}
        user = CustomUser.objects.create(telegram_id=300)
        CustomerDevice.objects.create(customer=user, fcm_token="tok-push-1", platform="android")
        msg = BroadcastMessage.objects.create(message_text="Push test", send_to_all=True)

        asyncio.run(send_with_django(msg.id, self.bot))

        # Telegram NOT called
        self.assertEqual(len(self.bot.sent_messages), 0)
        # Delivery created with channel=push
        delivery = NewsletterDelivery.objects.get(message=msg, customer=user)
        self.assertEqual(delivery.channel, "push")
        self.assertIsNone(delivery.telegram_message_id)
        self.assertIsNone(delivery.open_token)
        # Notification created
        notif = Notification.objects.get(user=user, type="broadcast")
        self.assertEqual(notif.body, "Push test")
        self.assertEqual(delivery.notification_id, notif.id)

    @patch("apps.notifications.tasks.send_push_notification_task.delay")
    def test_mixed_users_split_correctly(self, mock_push):
        mock_push.return_value = {"sent": 1, "success": 1, "failure": 0}
        push_user = CustomUser.objects.create(telegram_id=600)
        CustomerDevice.objects.create(customer=push_user, fcm_token="tok-mix-1", platform="ios")
        tg_user = CustomUser.objects.create(telegram_id=601)
        msg = BroadcastMessage.objects.create(message_text="Mixed", send_to_all=True)

        asyncio.run(send_with_django(msg.id, self.bot))

        # Telegram only for tg_user
        self.assertEqual(len(self.bot.sent_messages), 1)
        self.assertEqual(self.bot.sent_messages[0]["chat_id"], tg_user.telegram_id)
        # Check channels
        push_d = NewsletterDelivery.objects.get(customer=push_user, message=msg)
        self.assertEqual(push_d.channel, "push")
        tg_d = NewsletterDelivery.objects.get(customer=tg_user, message=msg)
        self.assertEqual(tg_d.channel, "telegram")

    @patch("apps.notifications.tasks.send_push_notification_task.delay")
    def test_category_promo_filters(self, mock_push):
        mock_push.return_value = {"sent": 1, "success": 1, "failure": 0}
        subscribed = CustomUser.objects.create(telegram_id=900, promo_enabled=True)
        unsubscribed = CustomUser.objects.create(telegram_id=901, promo_enabled=False)
        msg = BroadcastMessage.objects.create(
            message_text="Sale!", send_to_all=True, category="promo"
        )

        asyncio.run(send_with_django(msg.id, self.bot))

        delivered_ids = set(
            NewsletterDelivery.objects.filter(message=msg).values_list("customer_id", flat=True)
        )
        self.assertIn(subscribed.id, delivered_ids)
        self.assertNotIn(unsubscribed.id, delivered_ids)

    @patch("apps.notifications.tasks.send_push_notification_task.delay")
    def test_category_general_filters(self, mock_push):
        mock_push.return_value = {"sent": 1, "success": 1, "failure": 0}
        subscribed = CustomUser.objects.create(telegram_id=910, general_enabled=True)
        unsubscribed = CustomUser.objects.create(telegram_id=911, general_enabled=False)
        msg = BroadcastMessage.objects.create(
            message_text="Announcement", send_to_all=True, category="general"
        )

        asyncio.run(send_with_django(msg.id, self.bot))

        delivered_ids = set(
            NewsletterDelivery.objects.filter(message=msg).values_list("customer_id", flat=True)
        )
        self.assertIn(subscribed.id, delivered_ids)
        self.assertNotIn(unsubscribed.id, delivered_ids)

    @patch("apps.notifications.tasks.send_push_notification_task.delay")
    def test_push_delivery_idempotent(self, mock_push):
        mock_push.return_value = {"sent": 1, "success": 1, "failure": 0}
        user = CustomUser.objects.create(telegram_id=800)
        CustomerDevice.objects.create(customer=user, fcm_token="tok-idem", platform="android")
        msg = BroadcastMessage.objects.create(message_text="Idem", send_to_all=True)

        for _ in range(2):
            asyncio.run(send_with_django(msg.id, self.bot))

        self.assertEqual(NewsletterDelivery.objects.filter(message=msg).count(), 1)
        self.assertEqual(Notification.objects.filter(user=user, type="broadcast").count(), 1)
