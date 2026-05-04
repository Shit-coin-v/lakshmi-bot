from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff
from apps.main.models import CustomUser
from apps.orders.models import Order


class OrderListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Используем уникальные telegram_id и явные card_id вне диапазона auto-gen
        cls.alice = CustomUser.objects.create(
            full_name="Алиса", phone="+7 1", telegram_id=190001, card_id="LC-090001",
        )
        cls.bob = CustomUser.objects.create(
            full_name="Боб", phone="+7 2", telegram_id=190002, card_id="LC-090002",
        )
        cls.o1 = Order.objects.create(
            customer=cls.alice, status="new", address="x", phone="+7 1",
            total_price=Decimal("1500"), products_price=Decimal("1500"),
            fulfillment_type="delivery",
        )
        cls.o2 = Order.objects.create(
            customer=cls.bob, status="completed", address="x", phone="+7 2",
            total_price=Decimal("2500"), products_price=Decimal("2500"),
            fulfillment_type="pickup",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())
        self.url = reverse("crm_api:orders-list")

    def test_list_returns_orders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        ids = {o["id"] for o in response.data}
        self.assertIn(f"ORD-{self.o1.id}", ids)
        self.assertIn(f"ORD-{self.o2.id}", ids)

    def test_filter_by_status(self):
        response = self.client.get(self.url, {"status": "new"})
        self.assertEqual({o["status"] for o in response.data}, {"new"})

    def test_filter_by_purchase_type(self):
        response = self.client.get(self.url, {"purchaseType": "pickup"})
        self.assertEqual({o["purchaseType"] for o in response.data}, {"pickup"})

    def test_payload_shape(self):
        response = self.client.get(self.url)
        first = response.data[0]
        self.assertIn("clientId", first)
        self.assertIn("clientName", first)
        self.assertIn("amount", first)

    def test_n_plus_one_safe(self):
        for i in range(10):
            Order.objects.create(
                customer=self.alice, status="new", address="x", phone="+7",
                total_price=Decimal("100"), products_price=Decimal("100"),
                fulfillment_type="delivery",
            )
        # session + auth user + count + select_related query
        with self.assertNumQueries(4):
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
