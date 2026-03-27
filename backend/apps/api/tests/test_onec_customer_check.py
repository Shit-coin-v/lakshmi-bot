from __future__ import annotations

import json
from unittest.mock import patch

from django.conf import settings as django_settings

from apps.common import security
from apps.main.models import CustomUser
from .base import OneCTestBase


@patch("apps.common.security._ip_allowed", return_value=True)
class OneCCustomerCheckTests(OneCTestBase):
    def setUp(self):
        super().setUp()
        django_settings.ONEC_API_KEY = self.API_KEY

    def _post(self, payload: dict[str, object], **extra_headers):
        body = json.dumps(payload)
        headers = {"HTTP_X_API_KEY": security.API_KEY, **extra_headers}
        return self.client.post(
            "/onec/customer-check",
            data=body,
            content_type="application/json",
            **headers,
        )

    def _post_raw(self, body: str | bytes, **extra_headers):
        headers = {"HTTP_X_API_KEY": security.API_KEY, **extra_headers}
        return self.client.post(
            "/onec/customer-check",
            data=body,
            content_type="application/json",
            **headers,
        )

    # --- success: search by card_id ---

    def test_find_by_card_id(self, _ip):
        user = CustomUser.objects.create(telegram_id=9001)

        response = self._post({"card_id": user.card_id, "telegram_id": None})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["card_id"], user.card_id)

    # --- success: search by telegram_id ---

    def test_find_by_telegram_id(self, _ip):
        user = CustomUser.objects.create(telegram_id=9002)

        response = self._post({"telegram_id": "9002", "card_id": None})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["card_id"], user.card_id)

    # --- not found ---

    def test_unknown_card_id_returns_not_found(self, _ip):
        response = self._post({"card_id": "LC-999999", "telegram_id": None})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["card_id"], "Card not found")

    def test_unknown_telegram_id_returns_not_found(self, _ip):
        response = self._post({"telegram_id": "999999999", "card_id": None})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["card_id"], "Card not found")

    # --- user without card_id ---

    def test_user_without_card_id_returns_not_found(self, _ip):
        user = CustomUser.objects.create(telegram_id=7777)
        CustomUser.objects.filter(pk=user.pk).update(card_id=None)

        response = self._post({"telegram_id": "7777", "card_id": None})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["card_id"], "Card not found")

    # --- both fields null ---

    def test_both_null_returns_400(self, _ip):
        response = self._post({"card_id": None, "telegram_id": None})

        self.assertEqual(response.status_code, 400)

    # --- invalid body ---

    def test_empty_body_returns_400(self, _ip):
        response = self._post_raw(b"")

        self.assertEqual(response.status_code, 400)

    def test_invalid_json_returns_400(self, _ip):
        response = self._post_raw(b"{broken")

        self.assertEqual(response.status_code, 400)

    # --- auth ---

    def test_missing_api_key_returns_401(self, _ip):
        response = self.client.post(
            "/onec/customer-check",
            data=json.dumps({"card_id": "LC-000001", "telegram_id": None}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
