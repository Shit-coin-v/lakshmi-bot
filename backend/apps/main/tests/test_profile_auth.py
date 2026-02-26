import json
from unittest.mock import patch

from django.test import Client, TestCase

from apps.common import security
import apps.common.permissions as perms_module
from apps.main.models import CustomUser


class CustomerProfileAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create(
            telegram_id=55001, full_name="Test User", phone="+70001112233",
        )
        self.other_user = CustomUser.objects.create(
            telegram_id=55002, full_name="Other User",
        )

    def test_profile_get_without_header_returns_403(self):
        response = self.client.get(f"/api/customer/{self.user.pk}/")
        self.assertEqual(response.status_code, 403)

    def test_profile_get_own_returns_200(self):
        response = self.client.get(
            f"/api/customer/{self.user.pk}/",
            HTTP_X_TELEGRAM_USER_ID=str(self.user.telegram_id),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["telegram_id"], self.user.telegram_id)

    def test_profile_get_other_returns_404(self):
        """Accessing another user's profile returns 404 (not 403) to prevent enumeration."""
        response = self.client.get(
            f"/api/customer/{self.other_user.pk}/",
            HTTP_X_TELEGRAM_USER_ID=str(self.user.telegram_id),
        )
        self.assertEqual(response.status_code, 404)

    def test_profile_update_own_returns_200(self):
        response = self.client.patch(
            f"/api/customer/{self.user.pk}/",
            data=json.dumps({"full_name": "Updated Name"}),
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID=str(self.user.telegram_id),
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Name")

    def test_profile_update_other_returns_404(self):
        """Updating another user's profile returns 404 (not 403) to prevent enumeration."""
        response = self.client.patch(
            f"/api/customer/{self.other_user.pk}/",
            data=json.dumps({"full_name": "Hacked"}),
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID=str(self.user.telegram_id),
        )
        self.assertEqual(response.status_code, 404)


class SendMessageAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create(telegram_id=66001)
        security.API_KEY = "test-key"
        perms_module.API_KEY = "test-key"

    def tearDown(self):
        security.API_KEY = ""
        perms_module.API_KEY = ""

    def test_send_message_without_api_key_returns_403(self):
        response = self.client.post(
            "/api/send-message/",
            data=json.dumps({"telegram_id": self.user.telegram_id, "text": "Hello"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    @patch("apps.main.tasks.send_telegram_message_task.delay")
    def test_send_message_with_api_key_returns_200(self, mock_delay):
        response = self.client.post(
            "/api/send-message/",
            data=json.dumps({"telegram_id": self.user.telegram_id, "text": "Hello"}),
            content_type="application/json",
            HTTP_X_API_KEY="test-key",
        )
        self.assertEqual(response.status_code, 200)
        mock_delay.assert_called_once()
