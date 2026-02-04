import asyncio
from types import SimpleNamespace

from django.test import TransactionTestCase

from apps.main.models import BroadcastMessage, CustomUser, NewsletterDelivery
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
