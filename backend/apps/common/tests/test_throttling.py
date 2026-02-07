from django.core.cache import cache
from django.test import TestCase

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

from apps.common.throttling import TelegramUserThrottle
from apps.main.models import CustomUser, Product
from apps.orders.views import OrderListUserView, ProductListView

RATES = {"anon": "2/min", "telegram_user": "2/min"}


class AnonThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self._orig_classes = ProductListView.throttle_classes
        self._orig_rates = SimpleRateThrottle.THROTTLE_RATES
        ProductListView.throttle_classes = [AnonRateThrottle]
        SimpleRateThrottle.THROTTLE_RATES = RATES
        Product.objects.create(
            product_code="T1", name="Throttle Test", price="1.00", store_id=1,
        )

    def tearDown(self):
        ProductListView.throttle_classes = self._orig_classes
        SimpleRateThrottle.THROTTLE_RATES = self._orig_rates
        cache.clear()

    def test_anon_throttle_returns_429(self):
        # Direct view invocation bypassing URL resolver
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        view = ProductListView.as_view()

        # Verify patching
        self.assertEqual(ProductListView.throttle_classes, [AnonRateThrottle])
        self.assertEqual(SimpleRateThrottle.THROTTLE_RATES, RATES)

        statuses = []
        for i in range(4):
            request = factory.get("/api/products/")
            response = view(request)
            statuses.append(response.status_code)

        # first 2 should be 200, 3rd+ should be 429
        self.assertEqual(statuses[0], 200, f"All statuses: {statuses}")
        self.assertEqual(statuses[1], 200, f"All statuses: {statuses}")
        self.assertEqual(statuses[2], 429, f"All statuses: {statuses}")


class TelegramUserThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self._orig_classes = OrderListUserView.throttle_classes
        self._orig_rates = SimpleRateThrottle.THROTTLE_RATES
        OrderListUserView.throttle_classes = [TelegramUserThrottle]
        SimpleRateThrottle.THROTTLE_RATES = RATES
        self.customer = CustomUser.objects.create(telegram_id=90010)

    def tearDown(self):
        OrderListUserView.throttle_classes = self._orig_classes
        SimpleRateThrottle.THROTTLE_RATES = self._orig_rates
        cache.clear()

    def test_telegram_user_throttle_returns_429(self):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        view = OrderListUserView.as_view()

        statuses = []
        for i in range(4):
            request = factory.get(
                "/api/orders/",
                HTTP_X_TELEGRAM_USER_ID=str(self.customer.telegram_id),
            )
            response = view(request)
            statuses.append(response.status_code)

        self.assertEqual(statuses[0], 200, f"All statuses: {statuses}")
        self.assertEqual(statuses[1], 200, f"All statuses: {statuses}")
        self.assertEqual(statuses[2], 429, f"All statuses: {statuses}")
