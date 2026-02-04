import json
from django.test import TestCase, Client
from apps.common import security
from apps.orders.models import Product


class OneCStockSyncTests(TestCase):
    def setUp(self):
        security.API_KEY = 'test-key'
        self.client = Client()
        self.p1 = Product.objects.create(product_code='P001', name='Milk', price=100, store_id=0)
        self.p2 = Product.objects.create(product_code='P002', name='Bread', price=50, store_id=0)

    def _post(self, payload, api_key='test-key'):
        body = json.dumps(payload).encode()
        headers = {}
        if api_key:
            headers['HTTP_X_API_KEY'] = api_key
        return self.client.post(
            '/onec/stock', data=body, content_type='application/json',
            **headers,
        )

    def test_bulk_stock_update(self):
        resp = self._post({'items': [
            {'product_code': 'P001', 'stock': 10},
            {'product_code': 'P002', 'stock': 25},
        ]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['updated'], 2)
        self.assertEqual(data['not_found'], [])
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.stock, 10)
        self.assertEqual(self.p2.stock, 25)

    def test_partial_update_reports_not_found(self):
        resp = self._post({'items': [
            {'product_code': 'P001', 'stock': 5},
            {'product_code': 'P999', 'stock': 3},
        ]})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['updated'], 1)
        self.assertEqual(data['not_found'], ['P999'])
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 5)

    def test_empty_items_returns_400(self):
        resp = self._post({'items': []})
        self.assertEqual(resp.status_code, 400)

    def test_missing_api_key_returns_401(self):
        resp = self._post({'items': [{'product_code': 'P001', 'stock': 1}]}, api_key=None)
        self.assertEqual(resp.status_code, 401)

    def test_zero_stock_allowed(self):
        resp = self._post({'items': [{'product_code': 'P001', 'stock': 0}]})
        self.assertEqual(resp.status_code, 200)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 0)
