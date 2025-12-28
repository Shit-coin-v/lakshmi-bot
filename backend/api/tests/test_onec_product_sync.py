import json
from django.test import TestCase, Client
from api import security
from main.models import Product


class OneCProductSyncTests(TestCase):
    def setUp(self):
        security.API_KEY = 'test-key'
        self.client = Client()

    def _headers(self, body: bytes):
        return {
            'HTTP_X_API_KEY': security.API_KEY,
        }

    def test_create_and_update_product(self):
        payload = {
            'product_code': 'P001',
            'one_c_guid': 'GUID-1',
            'name': 'Milk',
            'price': '100.50',
            'category': 'Dairy',
            'is_promotional': True,
            'updated_at': '2025-09-01T12:00:00+09:00'
        }
        body = json.dumps(payload).encode()
        resp = self.client.post(
            '/onec/product', data=body, content_type='application/json',
            **self._headers(body)
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Product.objects.count(), 1)
        prod = Product.objects.get(product_code='P001')
        self.assertEqual(prod.name, 'Milk')
        self.assertTrue(prod.is_promotional)

        # update
        payload['name'] = 'Milk 2'
        body = json.dumps(payload).encode()
        resp = self.client.post(
            '/onec/product', data=body, content_type='application/json',
            **self._headers(body)
        )
        self.assertEqual(resp.status_code, 200)
        prod.refresh_from_db()
        self.assertEqual(prod.name, 'Milk 2')
