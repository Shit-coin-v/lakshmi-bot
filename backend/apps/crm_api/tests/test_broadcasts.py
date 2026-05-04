from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff
from apps.main.models import BroadcastMessage, NewsletterDelivery, CustomUser


class BroadcastHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        u1 = CustomUser.objects.create(
            full_name="X1", phone="+7 1", telegram_id=170001, card_id="LC-X-BR-1",
        )
        u2 = CustomUser.objects.create(
            full_name="X2", phone="+7 2", telegram_id=170002, card_id="LC-X-BR-2",
        )
        cls.b1 = BroadcastMessage.objects.create(
            message_text="Скидки", category="promo", send_to_all=True,
        )
        # 2 доставки на 2 разных клиента, одна открыта
        NewsletterDelivery.objects.create(
            message=cls.b1, customer=u1, channel="telegram", opened_at=timezone.now(),
        )
        NewsletterDelivery.objects.create(
            message=cls.b1, customer=u2, channel="telegram",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())
        self.url = reverse("crm_api:broadcasts-history")

    def test_list_returns_broadcasts(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_aggregates_reach_and_opened(self):
        response = self.client.get(self.url)
        b = response.data[0]
        self.assertEqual(b["reach"], 2)
        self.assertEqual(b["opened"], 1)

    def test_clicked_is_stub_zero(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data[0]["clicked"], 0)
