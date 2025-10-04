import json

from django.conf import settings
from django.test import Client, TestCase

from api import security
from main.models import Transaction, CustomUser


class OneCReceiptTests(TestCase):
    def setUp(self):
        security.API_KEY = 'test-key'
        self.client = Client()
        CustomUser.objects.update_or_create(
            telegram_id=settings.GUEST_TELEGRAM_ID,
            defaults={'full_name': 'Гость'},
        )

    def _headers(self, body: bytes):
        return {
            'HTTP_X_API_KEY': security.API_KEY,
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

        CustomUser.objects.create(telegram_id=payload['customer']['telegram_id'])

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

    def test_guest_receipt_records_transaction_without_bonuses(self):
        payload = {
            'receipt_guid': 'R-guest',
            'datetime': '2025-04-01T08:00:00+00:00',
            'store_id': '99',
            'customer': {},
            'positions': [
                {
                    'product_code': 'SKU-GUEST',
                    'name': 'Guest product',
                    'quantity': '1',
                    'price': '50.00',
                    'discount_amount': '0',
                    'is_promotional': False,
                    'line_number': 1,
                },
            ],
            'totals': {
                'total_amount': '50.00',
                'discount_total': '0',
                'bonus_spent': '0',
                'bonus_earned': '10.00',
            },
        }

        body = json.dumps(payload).encode()
        headers = {
            **self._headers(body),
            'HTTP_X_IDEMPOTENCY_KEY': '00000000-0000-0000-0000-000000000003',
        }

        resp = self.client.post(
            '/onec/receipt', data=body, content_type='application/json', follow=True, **headers
        )

        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data['customer']['telegram_id'], settings.GUEST_TELEGRAM_ID)
        self.assertEqual(data['totals']['bonus_earned'], 0.0)

        transaction = Transaction.objects.get(receipt_guid='R-guest')
        self.assertEqual(float(transaction.bonus_earned or 0), 0.0)

        guest = CustomUser.objects.get(telegram_id=settings.GUEST_TELEGRAM_ID)
        self.assertIsNone(guest.bonuses)

    def test_receipt_for_unknown_customer_returns_error(self):
        payload = {
            'receipt_guid': 'R-unknown',
            'datetime': '2025-05-01T10:00:00+00:00',
            'store_id': '101',
            'customer': {
                'telegram_id': 123456,
            },
            'positions': [
                {
                    'product_code': 'SKU-404',
                    'name': 'Missing user product',
                    'quantity': '1',
                    'price': '30.00',
                    'discount_amount': '0',
                    'is_promotional': False,
                    'line_number': 1,
                },
            ],
            'totals': {
                'total_amount': '30.00',
                'discount_total': '0',
                'bonus_spent': '0',
                'bonus_earned': '3.00',
            },
        }

        body = json.dumps(payload).encode()
        headers = {
            **self._headers(body),
            'HTTP_X_IDEMPOTENCY_KEY': '00000000-0000-0000-0000-000000000004',
        }

        resp = self.client.post(
            '/onec/receipt', data=body, content_type='application/json', follow=True, **headers
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['detail'], 'Клиент не найден. Пройдите регистрацию в боте.')
        self.assertEqual(Transaction.objects.count(), 0)
