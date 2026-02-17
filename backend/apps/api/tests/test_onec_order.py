import json

from apps.common import security
from .base import OneCTestBase


class OneCOrderCreateTests(OneCTestBase):
    def _post(self, payload, **extra):
        return self.client.post(
            "/onec/order",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=security.API_KEY,
            **extra,
        )

    def test_echo_order_id(self):
        response = self._post({"order_id": 42})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["order_id"], 42)
        self.assertIsNone(data["onec_guid"])

    def test_with_onec_guid(self):
        response = self._post({"order_id": 7, "onec_guid": "GUID-7"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["order_id"], 7)
        self.assertEqual(data["onec_guid"], "GUID-7")

    def test_missing_order_id_returns_400(self):
        response = self._post({"some_field": "value"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "missing_field")

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            "/onec/order",
            data="not json",
            content_type="application/json",
            HTTP_X_API_KEY=security.API_KEY,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "invalid_json")

    def test_missing_api_key_returns_401(self):
        response = self.client.post(
            "/onec/order",
            data=json.dumps({"order_id": 1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
