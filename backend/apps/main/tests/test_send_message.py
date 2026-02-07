import json
from unittest.mock import patch

from django.test import Client, TestCase

from apps.common import security
import apps.common.permissions as perms_module
from apps.main.models import CustomUser


class SendMessageAPIViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=8001)
        security.API_KEY = "test-key"
        perms_module.API_KEY = "test-key"

    def tearDown(self):
        security.API_KEY = ""
        perms_module.API_KEY = ""

    def _post(self, payload):
        return self.client.post(
            "/api/send-message/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY="test-key",
        )

    @patch("apps.main.tasks.send_telegram_message_task.delay")
    def test_send_success(self, mock_delay):
        response = self._post({"telegram_id": 8001, "text": "Hello!"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("msg", response.json())
        mock_delay.assert_called_once_with(8001, "Hello!")

    def test_user_not_found_returns_404(self):
        response = self._post({"telegram_id": 999999, "text": "Hello!"})
        self.assertEqual(response.status_code, 404)

    def test_missing_params_returns_400(self):
        response = self._post({"telegram_id": 8001})
        self.assertEqual(response.status_code, 400)

        response = self._post({"text": "Hello!"})
        self.assertEqual(response.status_code, 400)
