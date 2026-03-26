from __future__ import annotations

import json
from unittest.mock import patch

from django.conf import settings as django_settings

from apps.common import security
from apps.main.models import CustomUser
from .base import OneCTestBase


@patch("apps.common.security._ip_allowed", return_value=True)
class OneCCustomerLookupTests(OneCTestBase):
    def setUp(self):
        super().setUp()
        django_settings.ONEC_API_KEY = self.API_KEY

    def _post(self, payload: dict[str, object], **extra_headers):
        body = json.dumps(payload)
        headers = {"HTTP_X_API_KEY": security.API_KEY, **extra_headers}
        return self.client.post(
            "/onec/customer-lookup",
            data=body,
            content_type="application/json",
            **headers,
        )

    def _post_raw(self, body: str | bytes, **extra_headers):
        headers = {"HTTP_X_API_KEY": security.API_KEY, **extra_headers}
        return self.client.post(
            "/onec/customer-lookup",
            data=body,
            content_type="application/json",
            **headers,
        )

    # --- success ---

    def test_lookup_returns_card_id(self, _ip):
        user = CustomUser.objects.create(telegram_id=9001)

        response = self._post({"telegram_id": 9001})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["card_id"], user.card_id)

    def test_lookup_with_string_telegram_id(self, _ip):
        user = CustomUser.objects.create(telegram_id=9002)

        response = self._post({"telegram_id": "9002"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["card_id"], user.card_id)

    # --- missing / null ---

    def test_missing_telegram_id_returns_400(self, _ip):
        response = self._post({})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "missing_field")

    def test_null_telegram_id_returns_400(self, _ip):
        response = self._post({"telegram_id": None})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "missing_field")

    # --- invalid type ---

    def test_bool_true_returns_400(self, _ip):
        response = self._post({"telegram_id": True})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "invalid_field")

    def test_bool_false_returns_400(self, _ip):
        response = self._post({"telegram_id": False})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "invalid_field")

    def test_string_telegram_id_returns_400(self, _ip):
        response = self._post({"telegram_id": "not_a_number"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "invalid_field")

    # --- invalid JSON / body ---

    def test_empty_body_returns_400(self, _ip):
        response = self._post_raw(b"")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "invalid_json")

    def test_invalid_json_returns_400(self, _ip):
        response = self._post_raw(b"{broken")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "invalid_json")

    def test_root_array_returns_400(self, _ip):
        response = self._post_raw(json.dumps([1, 2, 3]))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "invalid_json")

    def test_root_string_returns_400(self, _ip):
        response = self._post_raw(json.dumps("abc"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "invalid_json")

    def test_root_number_returns_400(self, _ip):
        response = self._post_raw(json.dumps(123))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "invalid_json")

    def test_root_bool_returns_400(self, _ip):
        response = self._post_raw(json.dumps(True))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "invalid_json")

    # --- not found ---

    def test_unknown_telegram_id_returns_404(self, _ip):
        response = self._post({"telegram_id": 999999999})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error_code"], "customer_not_found")

    # --- card_id not assigned ---

    def test_user_without_card_id_returns_404(self, _ip):
        user = CustomUser.objects.create(telegram_id=7777)
        CustomUser.objects.filter(pk=user.pk).update(card_id="")

        response = self._post({"telegram_id": 7777})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error_code"], "card_id_not_assigned")

    # --- auth ---

    def test_missing_api_key_returns_401(self, _ip):
        response = self.client.post(
            "/onec/customer-lookup",
            data=json.dumps({"telegram_id": 9001}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
