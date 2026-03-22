import json
from decimal import Decimal

from apps.api.models import OneCClientMap
from apps.main.models import CustomUser
from .base import OneCTestBase


class OneCCustomersBatchSyncTests(OneCTestBase):
    URL = "/onec/customers/sync"

    def _post(self, payload, api_key="test-key"):
        body = json.dumps(payload).encode()
        headers = {}
        if api_key:
            headers["HTTP_X_API_KEY"] = api_key
        return self.client.post(
            self.URL, data=body, content_type="application/json", **headers,
        )

    # --- Happy path: create ---

    def test_create_new_customer(self):
        resp = self._post({"customers": [
            {
                "one_c_guid": "GUID-001",
                "first_name": "Иван",
                "last_name": "Петров",
                "phone": "+79001234567",
            },
        ]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["created"], 1)
        self.assertEqual(data["updated"], 0)
        self.assertEqual(data["errors"], [])
        self.assertTrue(OneCClientMap.objects.filter(one_c_guid="GUID-001").exists())
        user = OneCClientMap.objects.get(one_c_guid="GUID-001").user
        self.assertEqual(user.first_name, "Иван")
        self.assertEqual(user.last_name, "Петров")
        self.assertEqual(user.phone, "+79001234567")

    def test_create_customer_generates_placeholder_email(self):
        self._post({"customers": [{"one_c_guid": "GUID-EMAIL"}]})
        user = OneCClientMap.objects.get(one_c_guid="GUID-EMAIL").user
        self.assertTrue(user.email.startswith("onec-"))
        self.assertTrue(user.email.endswith("@onec.local"))

    def test_create_customer_with_bonuses(self):
        self._post({"customers": [
            {"one_c_guid": "GUID-B", "bonuses": "150.50"},
        ]})
        user = OneCClientMap.objects.get(one_c_guid="GUID-B").user
        self.assertEqual(user.bonuses, Decimal("150.50"))

    # --- Update existing ---

    def test_update_existing_customer_by_guid(self):
        user = CustomUser.objects.create(
            first_name="Old", email="existing@test.local",
        )
        OneCClientMap.objects.create(user=user, one_c_guid="GUID-UPD")

        resp = self._post({"customers": [
            {"one_c_guid": "GUID-UPD", "first_name": "New"},
        ]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["created"], 0)
        self.assertEqual(data["updated"], 1)
        user.refresh_from_db()
        self.assertEqual(user.first_name, "New")

    def test_update_bonuses(self):
        user = CustomUser.objects.create(
            bonuses=Decimal("100.00"), email="bonus@test.local",
        )
        OneCClientMap.objects.create(user=user, one_c_guid="GUID-BON")

        self._post({"customers": [
            {"one_c_guid": "GUID-BON", "bonuses": "250.00"},
        ]})
        user.refresh_from_db()
        self.assertEqual(user.bonuses, Decimal("250.00"))

    # --- Deduplication ---

    def test_batch_deduplication_last_wins(self):
        resp = self._post({"customers": [
            {"one_c_guid": "GUID-DUP", "first_name": "First"},
            {"one_c_guid": "GUID-DUP", "first_name": "Last"},
        ]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["created"], 1)
        user = OneCClientMap.objects.get(one_c_guid="GUID-DUP").user
        self.assertEqual(user.first_name, "Last")

    # --- Validation ---

    def test_empty_customers_returns_400(self):
        resp = self._post({"customers": []})
        self.assertEqual(resp.status_code, 400)

    def test_missing_customers_key_returns_400(self):
        resp = self._post({})
        self.assertEqual(resp.status_code, 400)

    # --- Auth ---

    def test_missing_api_key_returns_401(self):
        resp = self._post(
            {"customers": [{"one_c_guid": "X"}]},
            api_key=None,
        )
        self.assertEqual(resp.status_code, 401)

    # --- Invalid JSON ---

    def test_invalid_json_returns_400(self):
        headers = {"HTTP_X_API_KEY": "test-key"}
        resp = self.client.post(
            self.URL,
            data=b"not-json{{{",
            content_type="application/json",
            **headers,
        )
        self.assertEqual(resp.status_code, 400)
