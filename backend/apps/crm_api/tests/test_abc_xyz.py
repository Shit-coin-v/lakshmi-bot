from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.crm_api.tests._factories import create_staff


class AbcXyzTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_login(create_staff())
        self.url = reverse("crm_api:abc-xyz")

    def test_returns_three_matrices(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for key in ("matrixSku", "matrixRevenue", "matrixShare"):
            self.assertIn(key, response.data)
            self.assertEqual(
                set(response.data[key].keys()),
                {"AX", "AY", "AZ", "BX", "BY", "BZ", "CX", "CY", "CZ"},
            )

    def test_share_sums_to_100(self):
        response = self.client.get(self.url)
        s = sum(response.data["matrixShare"].values())
        self.assertAlmostEqual(s, 100.0, places=0)
