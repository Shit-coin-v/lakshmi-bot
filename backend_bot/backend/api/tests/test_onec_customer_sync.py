from __future__ import annotations

import json

from django.test import Client, TestCase

from api import security
from api.models import OneCClientMap
from main.models import CustomUser


class OneCCustomerSyncTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        self.client = Client()

    def _post(self, payload: dict[str, object], **extra_headers):
        body = json.dumps(payload)
        headers = {"HTTP_X_API_KEY": security.API_KEY, **extra_headers}
        return self.client.post(
            "/onec/customer",
            data=body,
            content_type="application/json",
            follow=True,
            **headers,
        )

    def test_lookup_by_qr_code(self):
        user = CustomUser.objects.create(telegram_id=9001, qr_code="QR-123")

        response = self._post({"qr_code": "QR-123"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "lookup")
        self.assertEqual(payload["customer"]["telegram_id"], user.telegram_id)
        self.assertEqual(payload["customer"]["qr_code"], user.qr_code)

    def test_assign_guid_via_qr_code(self):
        user = CustomUser.objects.create(telegram_id=42, qr_code="QR-42")

        response = self._post({"qr_code": "QR-42", "one_c_guid": "GUID-42"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        mapping = OneCClientMap.objects.get(one_c_guid="GUID-42")
        self.assertEqual(mapping.user_id, user.id)

    def test_missing_user_returns_404(self):
        response = self._post({"qr_code": "NOPE"})
        self.assertEqual(response.status_code, 404)
        self.assertIn("qr_code", response.json()["detail"])

    def test_mismatched_qr_and_telegram(self):
        CustomUser.objects.create(telegram_id=111, qr_code="QR-111")

        response = self._post({"qr_code": "QR-111", "telegram_id": 999})

        self.assertEqual(response.status_code, 400)
        self.assertIn("telegram_id", response.json()["detail"])

    def test_lookup_by_telegram_id_requires_existing_user(self):
        response = self._post({"telegram_id": 777})

        self.assertEqual(response.status_code, 404)
        self.assertFalse(CustomUser.objects.filter(telegram_id=777).exists())

    def test_lookup_by_telegram_id(self):
        user = CustomUser.objects.create(telegram_id=333)

        response = self._post({"telegram_id": 333})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "lookup")
        self.assertEqual(payload["customer"]["telegram_id"], user.telegram_id)


class OneCClientMapCascadeTests(TestCase):
    def test_deleting_user_cascades_map(self):
        user = CustomUser.objects.create(telegram_id=555)
        OneCClientMap.objects.create(user=user, one_c_guid="GUID-555")

        user.delete()

        self.assertEqual(OneCClientMap.objects.count(), 0)
