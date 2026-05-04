from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff
from apps.main.models import CustomUser
from apps.orders.models import Order

User = get_user_model()


class DashboardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.staff = create_staff()
        self.client.force_login(self.staff)
        self.url = reverse("crm_api:dashboard")

        # Тестовые данные — telegram_id обязателен (constraint: telegram_id OR email)
        c1 = CustomUser.objects.create(
            full_name="A", phone="+7 1", bonuses=Decimal("100"), telegram_id=100001
        )
        c2 = CustomUser.objects.create(
            full_name="B", phone="+7 2", bonuses=Decimal("250"), telegram_id=100002
        )
        # Заказы за неделю
        now = timezone.now()
        Order.objects.create(
            customer=c1, status="completed", address="x", phone="+7 1",
            total_price=Decimal("1500"), products_price=Decimal("1500"),
        )
        Order.objects.create(
            customer=c2, status="completed", address="x", phone="+7 2",
            total_price=Decimal("2500"), products_price=Decimal("2500"),
        )
        # И один сегодня
        Order.objects.create(
            customer=c1, status="new", address="x", phone="+7 1",
            total_price=Decimal("500"), products_price=Decimal("500"),
        )

    def test_dashboard_returns_kpis(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        kpis = {k["id"]: k for k in response.data["kpis"]}
        self.assertEqual(kpis["customers"]["value"], 2)
        self.assertEqual(kpis["bonuses"]["value"], 350)
        self.assertEqual(kpis["revenue"]["value"], 4000)
        self.assertGreaterEqual(kpis["orders"]["value"], 1)

    def test_dashboard_returns_daily_array(self):
        response = self.client.get(self.url)
        self.assertIn("daily", response.data)
        self.assertIsInstance(response.data["daily"], list)

    def test_dashboard_returns_active_campaigns(self):
        response = self.client.get(self.url)
        self.assertIn("activeCampaigns", response.data)
        self.assertIsInstance(response.data["activeCampaigns"], list)

    def test_dashboard_returns_rfm_segments(self):
        response = self.client.get(self.url)
        self.assertIn("rfmSegments", response.data)
        self.assertIsInstance(response.data["rfmSegments"], list)

    def test_dashboard_is_cached(self):
        # Первый запрос — кэш промахивается
        first = self.client.get(self.url)
        # Создаём ещё одного клиента
        CustomUser.objects.create(full_name="C", phone="+7 3", bonuses=Decimal("50"), telegram_id=100003)
        # Второй запрос — должен вернуть данные из кэша (без нового клиента)
        second = self.client.get(self.url)
        self.assertEqual(first.data["kpis"], second.data["kpis"])
        # Кэш сохраняет первоначальное значение — новый клиент не отражается
        customers_kpi = next(k for k in second.data["kpis"] if k["id"] == "customers")
        self.assertEqual(customers_kpi["value"], 2)  # 2 тестовых клиента, гость исключён, новый C не учтён из-за кэша

    def test_dashboard_unauthenticated_returns_401(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
