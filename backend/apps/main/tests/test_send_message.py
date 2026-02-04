import json
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase, override_settings

from apps.main.models import CustomUser


class SendMessageAPIViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=8001)

    def _post(self, payload):
        return self.client.post(
            "/api/send-message/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    @override_settings(TELEGRAM_BOT_TOKEN="fake-token")
    @patch("apps.main.views.requests.post")
    def test_send_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        response = self._post({"telegram_id": 8001, "text": "Hello!"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("msg", response.json())
        mock_post.assert_called_once()

    def test_user_not_found_returns_404(self):
        response = self._post({"telegram_id": 999999, "text": "Hello!"})
        self.assertEqual(response.status_code, 404)

    def test_missing_params_returns_400(self):
        response = self._post({"telegram_id": 8001})
        self.assertEqual(response.status_code, 400)

        response = self._post({"text": "Hello!"})
        self.assertEqual(response.status_code, 400)

    @override_settings(TELEGRAM_BOT_TOKEN="fake-token")
    @patch("apps.main.views.requests.post")
    def test_telegram_error_returns_502(self, mock_post):
        import requests as req
        mock_post.side_effect = req.RequestException("Timeout")

        response = self._post({"telegram_id": 8001, "text": "Hello!"})
        self.assertEqual(response.status_code, 502)
