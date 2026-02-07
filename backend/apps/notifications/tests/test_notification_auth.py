import json

from django.test import Client, TestCase

from apps.main.models import CustomUser, CustomerDevice, Notification


class NotificationAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = CustomUser.objects.create(telegram_id=50001)
        self.user2 = CustomUser.objects.create(telegram_id=50002)
        self.notif_user1 = Notification.objects.create(
            user=self.user1, title="For user1", body="Body1",
        )
        self.notif_user2 = Notification.objects.create(
            user=self.user2, title="For user2", body="Body2",
        )

    def test_list_without_header_returns_403(self):
        response = self.client.get("/api/notifications/")
        self.assertEqual(response.status_code, 403)

    def test_list_returns_only_own_notifications(self):
        response = self.client.get(
            "/api/notifications/",
            HTTP_X_TELEGRAM_USER_ID=str(self.user1.telegram_id),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], self.notif_user1.id)

        response2 = self.client.get(
            "/api/notifications/",
            HTTP_X_TELEGRAM_USER_ID=str(self.user2.telegram_id),
        )
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        self.assertEqual(len(data2), 1)
        self.assertEqual(data2[0]["id"], self.notif_user2.id)

    def test_retrieve_other_user_notification_returns_404(self):
        response = self.client.get(
            f"/api/notifications/{self.notif_user2.pk}/",
            HTTP_X_TELEGRAM_USER_ID=str(self.user1.telegram_id),
        )
        self.assertEqual(response.status_code, 404)

    def test_mark_read_other_user_notification_returns_404(self):
        response = self.client.post(
            f"/api/notifications/{self.notif_user2.pk}/read/",
            data=json.dumps({"source": "inapp"}),
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID=str(self.user1.telegram_id),
        )
        self.assertEqual(response.status_code, 404)

    def test_unread_count_returns_own_count_only(self):
        Notification.objects.create(
            user=self.user1, title="Extra", body="Extra body",
        )
        response = self.client.get(
            "/api/notifications/unread-count/",
            HTTP_X_TELEGRAM_USER_ID=str(self.user1.telegram_id),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["unread_count"], 2)

        response2 = self.client.get(
            "/api/notifications/unread-count/",
            HTTP_X_TELEGRAM_USER_ID=str(self.user2.telegram_id),
        )
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()["unread_count"], 1)

    def test_push_register_creates_device_for_authenticated_user(self):
        response = self.client.post(
            "/api/push/register/",
            data=json.dumps({
                "fcm_token": "push-auth-token-123",
                "platform": "android",
            }),
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID=str(self.user1.telegram_id),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        device = CustomerDevice.objects.get(fcm_token="push-auth-token-123")
        self.assertEqual(device.customer, self.user1)

    def test_fcm_update_creates_device_for_authenticated_user(self):
        response = self.client.post(
            "/api/fcm/token/",
            data=json.dumps({
                "fcm_token": "fcm-auth-token-456",
                "platform": "ios",
            }),
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID=str(self.user1.telegram_id),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["created"])
        device = CustomerDevice.objects.get(fcm_token="fcm-auth-token-456")
        self.assertEqual(device.customer, self.user1)
