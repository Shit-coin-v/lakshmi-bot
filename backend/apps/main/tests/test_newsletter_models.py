from django.db import IntegrityError
from django.test import TestCase

from apps.main.models import (
    BroadcastMessage,
    CustomUser,
    NewsletterDelivery,
    NewsletterOpenEvent,
)


class NewsletterModelsTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(telegram_id=555)
        self.message = BroadcastMessage.objects.create(message_text="promo", send_to_all=True)

    def test_create_delivery_and_event(self):
        delivery = NewsletterDelivery.objects.create(
            message=self.message,
            customer=self.user,
            chat_id=555,
            telegram_message_id=42,
            open_token="tokenuuid",
        )
        self.assertIsNone(delivery.opened_at)

        NewsletterOpenEvent.objects.create(
            delivery=delivery,
            telegram_user_id=self.user.telegram_id,
            raw_callback_data="open:tokenuuid",
        )
        self.assertEqual(NewsletterOpenEvent.objects.count(), 1)

    def test_open_token_unique(self):
        NewsletterDelivery.objects.create(
            message=self.message,
            customer=self.user,
            chat_id=555,
            telegram_message_id=1,
            open_token="duplicate",
        )
        with self.assertRaises(IntegrityError):
            NewsletterDelivery.objects.create(
                message=self.message,
                customer=self.user,
                chat_id=555,
                telegram_message_id=2,
                open_token="duplicate",
            )

    def test_open_event_unique_per_delivery(self):
        delivery = NewsletterDelivery.objects.create(
            message=self.message,
            customer=self.user,
            chat_id=555,
            telegram_message_id=1,
            open_token="unique-token",
        )

        NewsletterOpenEvent.objects.create(
            delivery=delivery,
            telegram_user_id=self.user.telegram_id,
        )

        with self.assertRaises(IntegrityError):
            NewsletterOpenEvent.objects.create(
                delivery=delivery,
                telegram_user_id=self.user.telegram_id,
            )
