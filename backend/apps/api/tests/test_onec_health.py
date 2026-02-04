import json

from django.test import Client, TestCase

from apps.common import security


class OneCHealthTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        self.client = Client()

    def test_health_returns_200(self):
        response = self.client.post(
            "/onec/health",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_X_API_KEY=security.API_KEY,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_missing_api_key_returns_401(self):
        response = self.client.post(
            "/onec/health",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
