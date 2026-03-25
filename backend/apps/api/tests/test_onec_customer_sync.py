from __future__ import annotations

import json

from django.test import TestCase

from apps.common import security
from apps.api.models import OneCClientMap
from apps.loyalty.models import CustomUser
from .base import OneCTestBase


class OneCCustomerSyncTests(OneCTestBase):
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

    def test_lookup_by_card_id(self):
        user = CustomUser.objects.create(telegram_id=9001)

        response = self._post({"card_id": user.card_id})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "lookup")
        self.assertEqual(payload["customer"]["card_id"], user.card_id)
        self.assertEqual(payload["customer"]["telegram_id"], user.telegram_id)

    def test_assign_guid_via_card_id(self):
        user = CustomUser.objects.create(telegram_id=42)

        response = self._post({"card_id": user.card_id, "one_c_guid": "GUID-42"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        from apps.api.models import OneCClientMap
        mapping = OneCClientMap.objects.get(one_c_guid="GUID-42")
        self.assertEqual(mapping.user_id, user.id)

    def test_missing_card_id_returns_400(self):
        response = self._post({})
        self.assertEqual(response.status_code, 400)
        self.assertIn("card_id", response.json()["detail"])

    def test_unknown_card_id_returns_404(self):
        response = self._post({"card_id": "LC-999999"})
        self.assertEqual(response.status_code, 404)
        self.assertIn("card_id", response.json()["detail"])

    def test_blank_card_id_returns_400(self):
        response = self._post({"card_id": "  "})
        self.assertEqual(response.status_code, 400)

    def test_card_id_in_response(self):
        user = CustomUser.objects.create(telegram_id=555, email="test@example.com")

        response = self._post({"card_id": user.card_id})

        self.assertEqual(response.status_code, 200)
        customer = response.json()["customer"]
        self.assertEqual(customer["card_id"], user.card_id)


class OneCClientMapCascadeTests(TestCase):
    def test_deleting_user_cascades_map(self):
        user = CustomUser.objects.create(telegram_id=555)
        OneCClientMap.objects.create(user=user, one_c_guid="GUID-555")

        user.delete()

        self.assertEqual(OneCClientMap.objects.count(), 0)
