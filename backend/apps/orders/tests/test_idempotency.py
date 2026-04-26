"""Тесты идемпотентности OrderCreate (Idempotency-Key header).

Закрывает Critical-блокер C2 из аудита — двойной POST с одинаковым ключом
не должен создавать два заказа.
"""
import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import Client, TestCase

from apps.main.models import CustomUser, Product
from apps.orders.models import DeliveryZone, Order

_YUKASSA = "apps.integrations.payments.yukassa_client"
_ONEC_DELAY = "apps.integrations.onec.tasks.send_order_to_onec.delay"


class OrderCreateIdempotencyTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.customer = CustomUser.objects.create(telegram_id=90001)
        Product.objects.create(
            product_code="IDEM-1", name="Idem Test", price="150.00", store_id=1,
        )
        DeliveryZone.objects.all().delete()
        Product.objects.create(
            product_code="DLV-IDEM", name="Доставка", price="200.00",
            store_id=0, is_active=True,
        )
        DeliveryZone.objects.create(name="Тест", product_code="DLV-IDEM", is_default=True)

    def _auth(self, **extra):
        return {"HTTP_X_TELEGRAM_USER_ID": str(self.customer.telegram_id), **extra}

    def _payload(self):
        return {
            "address": "ул. Тестовая, 1",
            "phone": "+79001112233",
            "payment_method": "cash",
            "fulfillment_type": "delivery",
            "delivery_zone_code": "DLV-IDEM",
            "items": [{"product_code": "IDEM-1", "quantity": 1}],
        }

    @patch(_ONEC_DELAY)
    def test_idempotent_replay_returns_same_order(self, _mock_onec):
        headers = self._auth(HTTP_IDEMPOTENCY_KEY="key-abc-123")

        r1 = self.client.post(
            "/api/orders/create/",
            data=json.dumps(self._payload()),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r1.status_code, 201)
        order_id = r1.json()["id"]

        r2 = self.client.post(
            "/api/orders/create/",
            data=json.dumps(self._payload()),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["id"], order_id)
        self.assertTrue(r2.json().get("idempotent_replay"))

        self.assertEqual(Order.objects.count(), 1)

    @patch(_ONEC_DELAY)
    def test_no_idempotency_key_creates_each_time(self, _mock_onec):
        for _ in range(2):
            r = self.client.post(
                "/api/orders/create/",
                data=json.dumps(self._payload()),
                content_type="application/json",
                **self._auth(),
            )
            self.assertEqual(r.status_code, 201)
        self.assertEqual(Order.objects.count(), 2)

    @patch(_ONEC_DELAY)
    def test_different_idempotency_keys_create_different_orders(self, _mock_onec):
        for key in ("key-1", "key-2"):
            r = self.client.post(
                "/api/orders/create/",
                data=json.dumps(self._payload()),
                content_type="application/json",
                **self._auth(HTTP_IDEMPOTENCY_KEY=key),
            )
            self.assertEqual(r.status_code, 201)
        self.assertEqual(Order.objects.count(), 2)

    @patch(f"{_YUKASSA}.create_payment")
    @patch(_ONEC_DELAY)
    def test_idempotent_replay_works_for_sbp(self, _mock_onec, mock_pay):
        mock_pay.return_value = {
            "payment_id": "pay_idem_1",
            "confirmation_url": "https://yookassa.ru/pay/idem",
            "status": "pending",
        }

        sbp_payload = {**self._payload(), "payment_method": "sbp"}
        headers = self._auth(HTTP_IDEMPOTENCY_KEY="sbp-key-1")

        r1 = self.client.post(
            "/api/orders/create/",
            data=json.dumps(sbp_payload),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r1.status_code, 201)

        r2 = self.client.post(
            "/api/orders/create/",
            data=json.dumps(sbp_payload),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.json().get("idempotent_replay"))

        # Вторая попытка не должна вызывать ЮKassa повторно.
        self.assertEqual(mock_pay.call_count, 1)
        self.assertEqual(Order.objects.count(), 1)
