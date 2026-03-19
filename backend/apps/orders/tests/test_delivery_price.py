from decimal import Decimal

from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from apps.main.models import CustomUser, Product
from apps.orders.models import DeliveryZone, Order

_TEST_OVERRIDES = dict(
    DELIVERY_PRICE_CACHE_TTL=600,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)


@override_settings(**_TEST_OVERRIDES)
class AppConfigViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        DeliveryZone.objects.all().delete()

    def test_config_public_no_auth(self):
        response = self.client.get("/api/config/")
        self.assertEqual(response.status_code, 200)

    def test_config_returns_delivery_zones(self):
        Product.objects.create(
            product_code="DLV-TEST",
            name="Доставка",
            price=Decimal("250.00"),
            store_id=0,
            is_active=True,
        )
        DeliveryZone.objects.create(
            name="Тест", product_code="DLV-TEST", is_default=True,
        )
        response = self.client.get("/api/config/")
        self.assertEqual(response.status_code, 200)
        zones = response.json()["delivery_zones"]
        self.assertEqual(len(zones), 1)
        self.assertEqual(zones[0]["price"], "250.00")
        self.assertTrue(zones[0]["is_default"])

    def test_config_excludes_zone_without_product(self):
        DeliveryZone.objects.create(
            name="Нет товара", product_code="MISSING", is_default=True,
        )
        response = self.client.get("/api/config/")
        self.assertEqual(response.json()["delivery_zones"], [])


@override_settings(**_TEST_OVERRIDES)
class CourierStatsTests(TestCase):
    """Courier stats total = sum of delivery_price from completed orders."""

    API_KEY = "test-key"

    def setUp(self):
        cache.clear()
        from apps.common import permissions, security
        security.API_KEY = self.API_KEY
        permissions.API_KEY = self.API_KEY
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=90001)

    def _create_completed_order(self, courier_tg_id, delivery_price):
        from django.utils import timezone
        return Order.objects.create(
            customer=self.customer,
            status="completed",
            delivered_by=courier_tg_id,
            completed_at=timezone.now(),
            address="Test",
            phone="+70001112233",
            products_price=Decimal("100"),
            delivery_price=Decimal(str(delivery_price)),
            total_price=Decimal("100") + Decimal(str(delivery_price)),
        )

    def test_mixed_delivery_prices(self):
        courier_id = 55555
        self._create_completed_order(courier_id, "200.00")
        self._create_completed_order(courier_id, "300.00")

        response = self.client.get(
            f"/api/bot/orders/completed-today/?courier_tg_id={courier_id}",
            HTTP_X_API_KEY=self.API_KEY,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["total"], "500.00")
