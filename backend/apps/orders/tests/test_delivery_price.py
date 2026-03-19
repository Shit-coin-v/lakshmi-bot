from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from apps.main.models import Product
from apps.orders.services import (
    DELIVERY_PRICE_CACHE_KEY,
    get_delivery_price,
    invalidate_delivery_price_cache,
)

TEST_DELIVERY_CODE = "TEST-DELIVERY"

_TEST_OVERRIDES = dict(
    DELIVERY_PRODUCT_CODE=TEST_DELIVERY_CODE,
    DELIVERY_PRICE_FALLBACK=Decimal("150.00"),
    DELIVERY_PRICE_CACHE_TTL=600,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)


@override_settings(**_TEST_OVERRIDES)
class GetDeliveryPriceTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_price_from_product(self):
        Product.objects.create(
            product_code=TEST_DELIVERY_CODE,
            name="Доставка",
            price=Decimal("200.00"),
            store_id=0,
            is_active=True,
        )
        self.assertEqual(get_delivery_price(), Decimal("200.00"))

    def test_fallback_when_product_missing(self):
        self.assertEqual(get_delivery_price(), Decimal("150.00"))

    def test_fallback_when_product_inactive(self):
        Product.objects.create(
            product_code=TEST_DELIVERY_CODE,
            name="Доставка",
            price=Decimal("200.00"),
            store_id=0,
            is_active=False,
        )
        self.assertEqual(get_delivery_price(), Decimal("150.00"))

    def test_price_is_cached(self):
        Product.objects.create(
            product_code=TEST_DELIVERY_CODE,
            name="Доставка",
            price=Decimal("200.00"),
            store_id=0,
            is_active=True,
        )
        get_delivery_price()
        cache_key = DELIVERY_PRICE_CACHE_KEY.format(code=TEST_DELIVERY_CODE)
        self.assertEqual(cache.get(cache_key), "200.00")

    def test_fallback_not_cached(self):
        get_delivery_price()
        cache_key = DELIVERY_PRICE_CACHE_KEY.format(code=TEST_DELIVERY_CODE)
        self.assertIsNone(cache.get(cache_key))

    def test_invalidate_cache_clears_entry(self):
        Product.objects.create(
            product_code=TEST_DELIVERY_CODE,
            name="Доставка",
            price=Decimal("200.00"),
            store_id=0,
            is_active=True,
        )
        get_delivery_price()  # populate cache
        invalidate_delivery_price_cache()
        cache_key = DELIVERY_PRICE_CACHE_KEY.format(code=TEST_DELIVERY_CODE)
        self.assertIsNone(cache.get(cache_key))

    def test_new_price_after_invalidation(self):
        p = Product.objects.create(
            product_code=TEST_DELIVERY_CODE,
            name="Доставка",
            price=Decimal("200.00"),
            store_id=0,
            is_active=True,
        )
        self.assertEqual(get_delivery_price(), Decimal("200.00"))

        p.price = Decimal("300.00")
        p.save(update_fields=["price"])
        invalidate_delivery_price_cache()

        self.assertEqual(get_delivery_price(), Decimal("300.00"))

    def test_custom_product_code(self):
        Product.objects.create(
            product_code="EXPRESS",
            name="Экспресс",
            price=Decimal("500.00"),
            store_id=0,
            is_active=True,
        )
        self.assertEqual(get_delivery_price("EXPRESS"), Decimal("500.00"))


@override_settings(**_TEST_OVERRIDES)
class AppConfigViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_config_public_no_auth(self):
        response = self.client.get("/api/config/")
        self.assertEqual(response.status_code, 200)

    def test_config_returns_delivery_price_from_product(self):
        Product.objects.create(
            product_code=TEST_DELIVERY_CODE,
            name="Доставка",
            price=Decimal("250.00"),
            store_id=0,
            is_active=True,
        )
        response = self.client.get("/api/config/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["delivery_price"], "250.00")

    def test_config_returns_fallback(self):
        response = self.client.get("/api/config/")
        self.assertEqual(response.json()["delivery_price"], "150.00")


@override_settings(**_TEST_OVERRIDES)
class CourierStatsDeliveryPriceTests(TestCase):
    """Verify courier stats total uses get_delivery_price."""

    @patch("apps.orders.services.get_delivery_price", return_value=Decimal("250.00"))
    def test_courier_rate_uses_get_delivery_price(self, _mock):
        from apps.bot_api.views import _get_courier_rate
        self.assertEqual(_get_courier_rate(), Decimal("250.00"))
