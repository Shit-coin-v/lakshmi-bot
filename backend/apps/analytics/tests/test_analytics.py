import json

from django.test import Client, TestCase

from apps.analytics.models import AnalyticsEvent
from apps.main.models import CustomUser


class AnalyticsEventViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=90001)

    def _headers(self):
        return {"HTTP_X_TELEGRAM_USER_ID": str(self.customer.telegram_id)}

    def _post(self, data, **extra_headers):
        return self.client.post(
            "/api/analytics/events/",
            data=json.dumps(data),
            content_type="application/json",
            **self._headers(),
            **extra_headers,
        )

    def test_create_screen_view_event(self):
        response = self._post({
            "event_type": "screen_view",
            "screen": "product_detail",
            "payload": {"product_id": 42},
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        self.assertEqual(event.event_type, "screen_view")
        self.assertEqual(event.screen, "product_detail")
        self.assertEqual(event.payload, {"product_id": 42})
        self.assertEqual(event.user, self.customer)

    def test_create_session_start_event(self):
        response = self._post({
            "event_type": "session_start",
            "payload": {"platform": "android", "app_version": "1.2.0"},
        })
        self.assertEqual(response.status_code, 201)
        event = AnalyticsEvent.objects.first()
        self.assertEqual(event.event_type, "session_start")

    def test_create_cart_add_event(self):
        response = self._post({
            "event_type": "cart_add",
            "payload": {"product_id": 5, "quantity": 2},
        })
        self.assertEqual(response.status_code, 201)

    def test_create_search_event(self):
        response = self._post({
            "event_type": "search",
            "payload": {"query": "торт", "results_count": 5},
        })
        self.assertEqual(response.status_code, 201)

    def test_create_promo_click_event(self):
        response = self._post({
            "event_type": "promo_click",
            "payload": {"promo_id": 7, "source": "banner"},
        })
        self.assertEqual(response.status_code, 201)

    def test_invalid_event_type_returns_400(self):
        response = self._post({
            "event_type": "invalid_type",
        })
        self.assertEqual(response.status_code, 400)

    def test_missing_event_type_returns_400(self):
        response = self._post({
            "screen": "home",
        })
        self.assertEqual(response.status_code, 400)

    def test_empty_payload_ok(self):
        response = self._post({
            "event_type": "session_end",
        })
        self.assertEqual(response.status_code, 201)
        event = AnalyticsEvent.objects.first()
        self.assertEqual(event.payload, {})

    def test_missing_auth_returns_403(self):
        response = self.client.post(
            "/api/analytics/events/",
            data=json.dumps({"event_type": "screen_view"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_user_set_from_header(self):
        response = self._post({
            "event_type": "screen_view",
            "screen": "home",
        })
        self.assertEqual(response.status_code, 201)
        event = AnalyticsEvent.objects.first()
        self.assertEqual(event.user_id, self.customer.id)
