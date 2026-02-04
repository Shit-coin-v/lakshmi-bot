import json

from django.test import Client, TestCase

from apps.common import security
from apps.common import permissions as _permissions_mod
from apps.main.models import (
    CustomUser,
    CustomerDevice,
    Notification,
    NotificationOpenEvent,
)


class NotificationViewSetTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        _permissions_mod.API_KEY = "test-key"
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=11001)
        self.notification = Notification.objects.create(
            user=self.customer,
            title="Test",
            body="Test body",
        )

    def _headers(self):
        return {"HTTP_X_API_KEY": security.API_KEY}

    def test_list_notifications(self):
        response = self.client.get(
            f"/api/notifications/?user_id={self.customer.id}",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Test")

    def test_retrieve_notification(self):
        response = self.client.get(
            f"/api/notifications/{self.notification.pk}/?user_id={self.customer.id}",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.notification.id)

    def test_notification_not_found_returns_404(self):
        response = self.client.get(
            f"/api/notifications/99999/?user_id={self.customer.id}",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 404)

    def test_unread_count(self):
        Notification.objects.create(
            user=self.customer, title="N2", body="Body2",
        )
        response = self.client.get(
            f"/api/notifications/unread-count/?user_id={self.customer.id}",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["unread_count"], 2)

    def test_mark_read(self):
        response = self.client.post(
            f"/api/notifications/{self.notification.pk}/read/",
            data=json.dumps({"user_id": self.customer.id}),
            content_type="application/json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
        self.assertTrue(
            NotificationOpenEvent.objects.filter(
                notification=self.notification,
            ).exists()
        )

    def test_missing_api_key_returns_403(self):
        response = self.client.get(
            f"/api/notifications/?user_id={self.customer.id}",
        )
        self.assertEqual(response.status_code, 403)


class PushRegisterViewTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        _permissions_mod.API_KEY = "test-key"
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=12001)

    def _headers(self):
        return {"HTTP_X_API_KEY": security.API_KEY}

    def test_push_register_creates_device(self):
        response = self.client.post(
            "/api/push/register/",
            data=json.dumps({
                "customer_id": self.customer.id,
                "fcm_token": "token-abc-123",
                "platform": "android",
            }),
            content_type="application/json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertTrue(
            CustomerDevice.objects.filter(fcm_token="token-abc-123").exists()
        )

    def test_push_register_missing_fields_returns_400(self):
        response = self.client.post(
            "/api/push/register/",
            data=json.dumps({"platform": "ios"}),
            content_type="application/json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 400)

    def test_push_register_missing_api_key_returns_403(self):
        response = self.client.post(
            "/api/push/register/",
            data=json.dumps({
                "customer_id": self.customer.id,
                "fcm_token": "token-xyz",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


class UpdateFCMTokenViewTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        _permissions_mod.API_KEY = "test-key"
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=13001)

    def _headers(self):
        return {"HTTP_X_API_KEY": security.API_KEY}

    def test_fcm_token_update(self):
        response = self.client.post(
            "/api/fcm/token/",
            data=json.dumps({
                "customer_id": self.customer.id,
                "fcm_token": "fcm-new-token",
                "platform": "ios",
            }),
            content_type="application/json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["created"])
        self.assertTrue(
            CustomerDevice.objects.filter(
                fcm_token="fcm-new-token", platform="ios",
            ).exists()
        )

    def test_fcm_token_user_not_found_returns_404(self):
        response = self.client.post(
            "/api/fcm/token/",
            data=json.dumps({
                "customer_id": 99999,
                "fcm_token": "fcm-token",
            }),
            content_type="application/json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 404)

    def test_fcm_token_missing_api_key_returns_403(self):
        response = self.client.post(
            "/api/fcm/token/",
            data=json.dumps({
                "customer_id": self.customer.id,
                "fcm_token": "fcm-token",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
