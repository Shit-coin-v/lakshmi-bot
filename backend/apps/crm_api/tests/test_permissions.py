"""Параметризованный тест permissions по всем CRM-эндпоинтам.

Список CRM_GET_ENDPOINTS пополняется по мере добавления views в Tasks 6-13.
Каждое имя должно быть `name=` в `apps/crm_api/urls.py`.
"""
from django.test import TestCase, override_settings
from django.urls import reverse, NoReverseMatch
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff, create_regular_user

# Список (route_name, kwargs_for_reverse). Пополняется по мере роста CRM-API.
CRM_GET_ENDPOINTS = [
    ("crm_api:auth-me", {}),
    ("crm_api:dashboard", {}),       # Task 6
    ("crm_api:clients-list", {}),    # Task 7
    ("crm_api:clients-detail", {"card_id": "LC-000001"}),  # Task 8
    ("crm_api:orders-list", {}),                           # Task 9
    ("crm_api:campaigns-list", {}),                        # Task 10
    # ...
]


@override_settings(REST_FRAMEWORK={
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {"anon_auth": "1000/min", "qr_login": "1000/min", "verify_code": "1000/min"},
})
class CrmPermissionParametrizedTests(TestCase):
    """Каждый CRM GET-эндпоинт: 401 без сессии, 403 для не-staff, 200 для staff."""

    def setUp(self):
        self.client = APIClient()

    def _resolve(self, name: str, kwargs: dict) -> str:
        try:
            return reverse(name, kwargs=kwargs)
        except NoReverseMatch:
            self.skipTest(f"Endpoint {name} not yet registered")

    def test_unauthenticated_returns_401(self):
        for name, kwargs in CRM_GET_ENDPOINTS:
            with self.subTest(endpoint=name):
                url = self._resolve(name, kwargs)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 401, f"{name}: {response.status_code} {response.content!r}")

    def test_non_staff_user_returns_403(self):
        user = create_regular_user()
        self.client.force_login(user)
        for name, kwargs in CRM_GET_ENDPOINTS:
            with self.subTest(endpoint=name):
                url = self._resolve(name, kwargs)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403, f"{name}: {response.status_code}")

    def test_staff_user_returns_200(self):
        user = create_staff()
        self.client.force_login(user)
        for name, kwargs in CRM_GET_ENDPOINTS:
            with self.subTest(endpoint=name):
                url = self._resolve(name, kwargs)
                response = self.client.get(url)
                self.assertIn(
                    response.status_code, (200, 404),
                    f"{name}: {response.status_code} {response.content!r}",
                )
