import json

from django.conf import settings
from django.test import Client, TestCase

from api import security
from main.models import CustomUser, Transaction


class OneCReceiptTests(TestCase):
    def setUp(self):
        security.API_KEY = "test-key"
        self.client = Client()
        CustomUser.objects.update_or_create(
            telegram_id=settings.GUEST_TELEGRAM_ID,
            defaults={"full_name": "Гость"},
        )

    def _post_receipt(self, payload: dict, *, api_key: str | None = None, idem: str):
        body = json.dumps(payload).encode()
        headers = {
            "HTTP_X_IDEMPOTENCY_KEY": idem,
        }
        if api_key is not None:
            headers["HTTP_X_API_KEY"] = api_key
        return self.client.post(
            "/onec/receipt",
            data=body,
            content_type="application/json",
            follow=True,
            **headers,
        )

    def _base_payload(self) -> dict:
        return {
            "receipt_guid": "R-123",
            "datetime": "2025-03-10T12:30:00+00:00",
            "store_id": "77",
            "customer": {"telegram_id": 9001},
            "positions": [
                {
                    "product_code": "SKU-1",
                    "quantity": "1",
                    "price": "100.00",
                    "line_number": 1,
                }
            ],
            "totals": {
                "total_amount": "100.00",
                "discount_total": "0",
                "bonus_spent": "0",
                "bonus_earned": "10.00",
            },
        }

    def test_valid_receipt_returns_201(self):
        payload = self._base_payload()
        CustomUser.objects.create(telegram_id=payload["customer"]["telegram_id"])

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000001",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["created_count"], 1)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_guest_receipt_returns_201(self):
        payload = self._base_payload()
        payload["receipt_guid"] = "R-guest"
        payload["customer"] = {}

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000002",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["customer"]["telegram_id"], settings.GUEST_TELEGRAM_ID)
        self.assertEqual(data["totals"]["bonus_earned"], 0.0)

    def test_missing_required_field_returns_structured_error(self):
        payload = self._base_payload()
        payload.pop("receipt_guid")

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000003",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error_code"], "missing_field")
        self.assertIn("receipt_guid", data["details"])

    def test_duplicate_line_returns_duplicate_receipt_line_error(self):
        payload = self._base_payload()
        CustomUser.objects.create(telegram_id=payload["customer"]["telegram_id"])
        payload["positions"].append(
            {
                "product_code": "SKU-2",
                "quantity": "1",
                "price": "50.00",
                "line_number": 1,
            }
        )

        response = self._post_receipt(
            payload,
            api_key=security.API_KEY,
            idem="00000000-0000-0000-0000-000000000004",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error_code"], "duplicate_receipt_line")
        self.assertTrue(data["details"])  # ensure diagnostics present

    def test_invalid_or_missing_api_key_returns_401(self):
        payload = self._base_payload()

        response_missing = self._post_receipt(
            payload,
            api_key=None,
            idem="00000000-0000-0000-0000-000000000005",
        )
        self.assertEqual(response_missing.status_code, 401)

        response_wrong = self._post_receipt(
            payload,
            api_key="wrong",
            idem="00000000-0000-0000-0000-000000000006",
        )
        self.assertEqual(response_wrong.status_code, 401)
