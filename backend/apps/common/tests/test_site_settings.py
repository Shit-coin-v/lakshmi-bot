import json
from unittest.mock import patch

from django.test import Client, TestCase

from apps.common.models import SiteSettings
from apps.main.models import CustomUser, Product


class SiteSettingsSingletonTests(TestCase):
    def test_load_creates_default(self):
        self.assertEqual(SiteSettings.objects.count(), 0)
        settings = SiteSettings.load()
        self.assertEqual(settings.pk, 1)
        self.assertTrue(settings.delivery_enabled)
        self.assertTrue(settings.pickup_enabled)

    def test_save_always_pk_1(self):
        s = SiteSettings(pk=99, delivery_enabled=False)
        s.save()
        self.assertEqual(s.pk, 1)
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_delete_does_nothing(self):
        SiteSettings.load()
        SiteSettings.objects.get(pk=1).delete()
        self.assertEqual(SiteSettings.objects.count(), 1)


class FulfillmentDisabledTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=90001)
        self.product = Product.objects.create(
            product_code="SET-1", name="Test", price="10.00", store_id=1,
        )
        self.headers = {"HTTP_X_TELEGRAM_USER_ID": str(self.customer.telegram_id)}

    def _order_payload(self, fulfillment_type="delivery"):
        return {
            "address": "ул. Тестовая, 1",
            "phone": "+79001112233",
            "payment_method": "cash",
            "fulfillment_type": fulfillment_type,
            "items": [{"product_code": "SET-1", "quantity": 1}],
        }

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_delivery_disabled_returns_400(self, _mock):
        settings = SiteSettings.load()
        settings.delivery_enabled = False
        settings.delivery_disabled_message = "Доставка закрыта до завтра"
        settings.save()

        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(self._order_payload("delivery")),
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Доставка закрыта до завтра", str(response.json()))

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_pickup_disabled_returns_400(self, _mock):
        settings = SiteSettings.load()
        settings.pickup_enabled = False
        settings.pickup_disabled_message = "Самовывоз недоступен"
        settings.save()

        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(self._order_payload("pickup")),
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Самовывоз недоступен", str(response.json()))

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_delivery_enabled_passes(self, _mock):
        # По дефолту всё включено
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(self._order_payload("delivery")),
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 201)

    @patch("apps.integrations.onec.tasks.send_order_to_onec.delay")
    def test_pickup_enabled_passes(self, _mock):
        response = self.client.post(
            "/api/orders/create/",
            data=json.dumps(self._order_payload("pickup")),
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 201)
