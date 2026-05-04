from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff
from apps.main.models import CustomUser


class ClientListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # card_id не передаём — модель автогенерирует LC-{pk:06d}.
        # Это исключает коллизию с guest-пользователем из миграции 0008.
        cls.alice = CustomUser.objects.create(
            full_name="Алиса Иванова", phone="+7 914 111-22-33",
            email="alice@example.ru", bonuses=Decimal("500"),
            total_spent=Decimal("12000"), purchase_count=5,
        )
        cls.alice.refresh_from_db()  # подтягиваем автогенерированный card_id

        cls.bob = CustomUser.objects.create(
            full_name="Боб Петров", phone="+7 914 222-33-44",
            email="bob@example.ru", bonuses=Decimal("0"),
            total_spent=Decimal("0"), purchase_count=0,
        )
        cls.bob.refresh_from_db()

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())
        self.url = reverse("crm_api:clients-list")

    def _lc_ids(self, response):
        """Извлечь LC-* идентификаторы (исключая guest user из миграции 0008)."""
        return {c["id"] for c in response.data if c["id"] and c["id"].startswith("LC-")}

    def _alice_id(self):
        return self.alice.card_id

    def _bob_id(self):
        return self.bob.card_id

    def test_list_returns_all(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        lc_ids = self._lc_ids(response)
        self.assertIn(self._alice_id(), lc_ids)
        self.assertIn(self._bob_id(), lc_ids)

    def test_search_by_name(self):
        response = self.client.get(self.url, {"q": "Алис"})
        lc_ids = self._lc_ids(response)
        self.assertIn(self._alice_id(), lc_ids)
        self.assertNotIn(self._bob_id(), lc_ids)

    def test_search_by_phone(self):
        response = self.client.get(self.url, {"q": "111-22-33"})
        lc_ids = self._lc_ids(response)
        self.assertIn(self._alice_id(), lc_ids)
        self.assertNotIn(self._bob_id(), lc_ids)

    def test_search_by_card_id(self):
        response = self.client.get(self.url, {"q": self._bob_id()})
        lc_ids = self._lc_ids(response)
        self.assertIn(self._bob_id(), lc_ids)
        self.assertNotIn(self._alice_id(), lc_ids)

    def test_pagination_headers(self):
        response = self.client.get(self.url, {"page_size": 1})
        self.assertEqual(len(response.data), 1)
        # X-Total-Count учитывает всех пользователей (включая guest из миграции)
        self.assertEqual(response.headers.get("X-Page-Size"), "1")
        # Проверяем только наличие заголовка, значение зависит от фикстур
        self.assertIn("X-Total-Count", response.headers)

    def test_n_plus_one_safe(self):
        # Создаём ещё клиентов; запрос должен оставаться в разумных пределах
        for i in range(10):
            CustomUser.objects.create(
                full_name=f"User {i}", phone=f"+7 {i:04d}",
                telegram_id=200000 + i,
            )
        with self.assertNumQueries(4):  # session+user+count+select_clients (с join rfm_profile)
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)

    def test_serializer_outputs_camelcase(self):
        response = self.client.get(self.url)
        first = next(c for c in response.data if c["id"] and c["id"].startswith("LC-"))
        self.assertIn("rfmSegment", first)
        self.assertIn("purchaseCount", first)
        self.assertIn("lastOrder", first)
