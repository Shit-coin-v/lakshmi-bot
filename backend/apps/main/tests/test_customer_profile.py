import json

from django.test import Client, TestCase

from apps.main.models import CustomUser


class CustomerProfileViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(
            telegram_id=9001,
            full_name="Test User",
            phone="+70001112233",
            bonuses=100,
        )

    def test_get_profile(self):
        response = self.client.get(
            f"/api/customer/{self.customer.pk}/",
            HTTP_X_TELEGRAM_USER_ID=str(self.customer.telegram_id),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["telegram_id"], 9001)
        self.assertEqual(data["full_name"], "Test User")
        self.assertEqual(data["phone"], "+70001112233")

    def test_patch_profile(self):
        response = self.client.patch(
            f"/api/customer/{self.customer.pk}/",
            data=json.dumps({"full_name": "Updated Name"}),
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID=str(self.customer.telegram_id),
        )
        self.assertEqual(response.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.full_name, "Updated Name")

    def test_not_found_returns_404(self):
        response = self.client.get(
            "/api/customer/99999/",
            HTTP_X_TELEGRAM_USER_ID=str(self.customer.telegram_id),
        )
        self.assertEqual(response.status_code, 404)

    def test_readonly_fields_not_changed(self):
        response = self.client.patch(
            f"/api/customer/{self.customer.pk}/",
            data=json.dumps({"bonuses": 999, "telegram_id": 1111}),
            content_type="application/json",
            HTTP_X_TELEGRAM_USER_ID=str(self.customer.telegram_id),
        )
        self.assertEqual(response.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(float(self.customer.bonuses), 100.0)
        self.assertEqual(self.customer.telegram_id, 9001)
