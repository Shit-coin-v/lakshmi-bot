import json

from apps.main.models import Category
from .base import OneCTestBase


class OneCCategorySyncTests(OneCTestBase):
    URL = "/onec/categories/sync"

    def _post(self, payload, api_key="test-key"):
        body = json.dumps(payload).encode()
        headers = {}
        if api_key:
            headers["HTTP_X_API_KEY"] = api_key
        return self.client.post(
            self.URL, data=body, content_type="application/json", **headers,
        )

    # --- Happy path ---

    def test_create_single_category(self):
        resp = self._post({"categories": [
            {"external_id": "CAT-1", "name": "Молоко"},
        ]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["created"], 1)
        self.assertEqual(data["updated"], 0)
        self.assertTrue(
            Category.objects.filter(external_id="CAT-1", name="Молоко").exists(),
        )

    def test_create_multiple_categories(self):
        resp = self._post({"categories": [
            {"external_id": "CAT-1", "name": "Молоко"},
            {"external_id": "CAT-2", "name": "Хлеб"},
        ]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["created"], 2)
        self.assertEqual(Category.objects.count(), 2)

    # --- Update ---

    def test_update_existing_category(self):
        Category.objects.create(external_id="CAT-1", name="Old Name")
        resp = self._post({"categories": [
            {"external_id": "CAT-1", "name": "New Name"},
        ]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["created"], 0)
        self.assertEqual(data["updated"], 1)
        cat = Category.objects.get(external_id="CAT-1")
        self.assertEqual(cat.name, "New Name")

    def test_update_is_active_and_sort_order(self):
        Category.objects.create(
            external_id="CAT-1", name="A", is_active=True, sort_order=0,
        )
        resp = self._post({"categories": [
            {"external_id": "CAT-1", "name": "A", "is_active": False, "sort_order": 5},
        ]})
        self.assertEqual(resp.status_code, 200)
        cat = Category.objects.get(external_id="CAT-1")
        self.assertFalse(cat.is_active)
        self.assertEqual(cat.sort_order, 5)

    # --- Parent linking (Pass 2) ---

    def test_parent_linking(self):
        resp = self._post({"categories": [
            {"external_id": "ROOT", "name": "Root"},
            {"external_id": "CHILD", "name": "Child", "parent_external_id": "ROOT"},
        ]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["parent_linked"], 1)
        child = Category.objects.get(external_id="CHILD")
        parent = Category.objects.get(external_id="ROOT")
        self.assertEqual(child.parent_id, parent.id)

    def test_parent_not_found_reports_error(self):
        resp = self._post({"categories": [
            {"external_id": "ORPHAN", "name": "Orphan", "parent_external_id": "MISSING"},
        ]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["errors"]), 1)
        self.assertEqual(data["errors"][0]["reason"], "parent_not_found")

    def test_null_parent_clears_existing_parent(self):
        root = Category.objects.create(external_id="ROOT", name="Root")
        Category.objects.create(external_id="CHILD", name="Child", parent=root)
        resp = self._post({"categories": [
            {"external_id": "CHILD", "name": "Child", "parent_external_id": None},
        ]})
        self.assertEqual(resp.status_code, 200)
        child = Category.objects.get(external_id="CHILD")
        self.assertIsNone(child.parent)

    # --- Validation errors ---

    def test_empty_categories_returns_400(self):
        resp = self._post({"categories": []})
        self.assertEqual(resp.status_code, 400)

    def test_missing_categories_key_returns_400(self):
        resp = self._post({})
        self.assertEqual(resp.status_code, 400)

    # --- Auth ---

    def test_missing_api_key_returns_401(self):
        resp = self._post(
            {"categories": [{"external_id": "X", "name": "X"}]},
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
        self.assertIn("invalid_json", resp.json().get("error_code", ""))
