import json

from django.test import Client, TestCase

from apps.main.models import (
    CustomUser,
    CustomerDevice,
    Notification,
    NotificationOpenEvent,
)


class NotificationViewSetTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=11001)
        self.notification = Notification.objects.create(
            user=self.customer,
            title="Test",
            body="Test body",
        )

    def _headers(self):
        return {"HTTP_X_TELEGRAM_USER_ID": str(self.customer.telegram_id)}

    def test_list_notifications(self):
        response = self.client.get(
            "/api/notifications/",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Test")

    def test_retrieve_notification(self):
        response = self.client.get(
            f"/api/notifications/{self.notification.pk}/",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.notification.id)

    def test_notification_not_found_returns_404(self):
        response = self.client.get(
            "/api/notifications/99999/",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 404)

    def test_unread_count(self):
        Notification.objects.create(
            user=self.customer, title="N2", body="Body2",
        )
        response = self.client.get(
            "/api/notifications/unread-count/",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["unread_count"], 2)

    def test_mark_read(self):
        response = self.client.post(
            f"/api/notifications/{self.notification.pk}/read/",
            data=json.dumps({"source": "inapp"}),
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

    def test_missing_header_returns_403(self):
        response = self.client.get("/api/notifications/")
        self.assertEqual(response.status_code, 403)


class PushRegisterViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=12001)

    def _headers(self):
        return {"HTTP_X_TELEGRAM_USER_ID": str(self.customer.telegram_id)}

    def test_push_register_creates_device(self):
        response = self.client.post(
            "/api/push/register/",
            data=json.dumps({
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

    def test_push_register_missing_token_returns_400(self):
        response = self.client.post(
            "/api/push/register/",
            data=json.dumps({"platform": "ios"}),
            content_type="application/json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 400)

    def test_push_register_missing_header_returns_403(self):
        response = self.client.post(
            "/api/push/register/",
            data=json.dumps({
                "fcm_token": "token-xyz",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


class UpdateFCMTokenViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=13001)

    def _headers(self):
        return {"HTTP_X_TELEGRAM_USER_ID": str(self.customer.telegram_id)}

    def test_fcm_token_update(self):
        response = self.client.post(
            "/api/fcm/token/",
            data=json.dumps({
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

    def test_fcm_token_missing_token_returns_400(self):
        response = self.client.post(
            "/api/fcm/token/",
            data=json.dumps({"platform": "ios"}),
            content_type="application/json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, 400)

    def test_fcm_token_missing_header_returns_403(self):
        response = self.client.post(
            "/api/fcm/token/",
            data=json.dumps({
                "fcm_token": "fcm-token",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
