from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff, create_regular_user


@override_settings(REST_FRAMEWORK={
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {"anon_auth": "1000/min", "qr_login": "1000/min", "verify_code": "1000/min"},
})
class LoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("crm_api:auth-login")

    def test_login_success_sets_session_cookie(self):
        user = create_staff(email="manager@lakshmi.ru", password="secret123")
        response = self.client.post(self.url, {"email": "manager@lakshmi.ru", "password": "secret123"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["user"]["email"], "manager@lakshmi.ru")
        self.assertIn("sessionid", response.cookies)
        self.assertIn("csrftoken", response.cookies)

    def test_login_email_case_insensitive(self):
        create_staff(email="manager@lakshmi.ru", password="secret123")
        response = self.client.post(self.url, {"email": "Manager@Lakshmi.RU", "password": "secret123"}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_login_wrong_password_returns_401(self):
        create_staff(email="manager@lakshmi.ru", password="secret123")
        response = self.client.post(self.url, {"email": "manager@lakshmi.ru", "password": "wrong"}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "Неверный email или пароль")

    def test_login_unknown_email_returns_401(self):
        response = self.client.post(self.url, {"email": "ghost@lakshmi.ru", "password": "any"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_login_non_staff_returns_403(self):
        create_regular_user(email="user@lakshmi.ru", password="secret123")
        response = self.client.post(self.url, {"email": "user@lakshmi.ru", "password": "secret123"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Нет доступа в CRM")

    def test_login_invalid_body_returns_400(self):
        response = self.client.post(self.url, {"email": "not-an-email"}, format="json")
        self.assertEqual(response.status_code, 400)


@override_settings(REST_FRAMEWORK={
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {"anon_auth": "1000/min", "qr_login": "1000/min", "verify_code": "1000/min"},
})
class LogoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("crm_api:auth-logout")

    def test_logout_returns_204_and_clears_session(self):
        user = create_staff()
        self.client.force_login(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 204)
        # повторный запрос /me/ — уже 401
        me_response = self.client.get(reverse("crm_api:auth-me"))
        self.assertEqual(me_response.status_code, 401)

    def test_logout_unauthenticated_returns_401(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 401)


class MeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("crm_api:auth-me")

    def test_me_unauthenticated_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_me_authenticated_returns_user(self):
        user = create_staff(email="manager@lakshmi.ru")
        user.first_name = "Иван"
        user.last_name = "Сидоров"
        user.save()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["email"], "manager@lakshmi.ru")
        self.assertEqual(response.data["user"]["name"], "Иван Сидоров")

    def test_me_sets_csrftoken_cookie(self):
        user = create_staff()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertIn("csrftoken", response.cookies)


@override_settings(REST_FRAMEWORK={
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {"anon_auth": "10/min"},
})
class LoginRateLimitTests(TestCase):
    """Login защищён AnonAuthThrottle (10/min). Проверяем, что 11-й запрос отбивается с 429."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # очистка throttle-state между тестами
        self.client = APIClient()
        self.url = reverse("crm_api:auth-login")

    def test_login_rate_limited_after_10_attempts(self):
        # DRF кеширует THROTTLE_RATES на уровне класса при импорте модуля,
        # поэтому @override_settings не достигает get_rate() напрямую.
        # Патчим THROTTLE_RATES непосредственно на классе.
        from apps.common.throttling import AnonAuthThrottle
        with mock.patch.object(AnonAuthThrottle, "THROTTLE_RATES", {"anon_auth": "10/min"}):
            # 10 запросов проходят (пусть и с 401), 11-й отбивается с 429
            for i in range(10):
                response = self.client.post(self.url, {"email": "ghost@example.com", "password": "x"}, format="json")
                self.assertNotEqual(response.status_code, 429, f"attempt {i+1}: throttled too early")
            response = self.client.post(self.url, {"email": "ghost@example.com", "password": "x"}, format="json")
            self.assertEqual(response.status_code, 429, f"11th attempt got {response.status_code}, expected 429")
