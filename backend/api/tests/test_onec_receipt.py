import json
import time
import hmac
import hashlib

from django.test import TestCase, Client

from api import security
from main.models import Transaction, CustomUser


class OneCReceiptTests(TestCase):
    def setUp(self):
        security.API_KEY = 'test-key'
        security.HMAC_SECRET = 'test-secret'
        security.DISABLE_HMAC = False
        self.client = Client()

    def _headers(self, body: bytes):
        ts = str(int(time.time()))
        sign = hmac.new(
            security.HMAC_SECRET.encode(),
            f"{ts}.".encode() + body,
            hashlib.sha256,
        ).hexdigest()
        return {
            'HTTP_X_API_KEY': security.API_KEY,
            'HTTP_X_TIMESTAMP': ts,
            'HTTP_X_SIGN': sign,
        }

    def test_repeat_receipt_does_not_duplicate_transactions(self):
        payload = {
            'receipt_guid': 'R-123',
            'datetime': '2025-03-10T12:30:00+00:00',
            'store_id': '77',
            'customer': {
                'telegram_id': 9001,
            },
            'positions': [
                {
                    'product_code': 'SKU-1',
                    'name': 'Test product',
                    'quantity': '2',
                    'price': '100.00',
                    'discount_amount': '10.00',
                    'is_promotional': False,
                    'line_number': 1,
                },
            ],
            'totals': {
                'total_amount': '180.00',
                'discount_total': '20.00',
                'bonus_spent': '0',
                'bonus_earned': '18.00',
            },
        }

        body = json.dumps(payload).encode()

        first_headers = {
            **self._headers(body),
            'HTTP_X_IDEMPOTENCY_KEY': '00000000-0000-0000-0000-000000000001',
        }
        resp = self.client.post(
            '/onec/receipt', data=body, content_type='application/json', follow=True, **first_headers
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['created_count'], 1)
        self.assertEqual(len(data['allocations']), 1)
        self.assertEqual(Transaction.objects.count(), 1)

        # repeat with a different idempotency key to simulate retry from 1C
        second_headers = {
            **self._headers(body),
            'HTTP_X_IDEMPOTENCY_KEY': '00000000-0000-0000-0000-000000000002',
        }
        resp_repeat = self.client.post(
            '/onec/receipt', data=body, content_type='application/json', follow=True, **second_headers
        )
        self.assertEqual(resp_repeat.status_code, 200)
        repeat_data = resp_repeat.json()
        self.assertEqual(repeat_data['status'], 'already exists')
        self.assertEqual(repeat_data['created_count'], 0)
        self.assertEqual(repeat_data['allocations'], [])
        self.assertEqual(Transaction.objects.count(), 1)

        user = CustomUser.objects.get(telegram_id=payload['customer']['telegram_id'])
        self.assertEqual(user.purchase_count, 1)
