import 'package:flutter_test/flutter_test.dart';
import 'package:lakshmi_market/features/orders/models/order_detail_model.dart';

void main() {
  group('OrderItemDetailModel', () {
    test('fromJson parses all fields', () {
      final json = {
        'product_code': 'SKU-001',
        'name': 'Widget',
        'quantity': '3',
        'price_at_moment': '49.99',
      };

      final item = OrderItemDetailModel.fromJson(json);

      expect(item.productCode, 'SKU-001');
      expect(item.name, 'Widget');
      expect(item.quantity, 3);
      expect(item.priceAtMoment, 49.99);
    });
  });

  group('OrderDetailModel', () {
    test('fromJson full parse with items', () {
      final json = {
        'id': '55',
        'created_at': '2025-03-20T14:00:00Z',
        'status': 'delivered',
        'status_display': 'Доставлен',
        'payment_method': 'card',
        'address': 'ул. Ленина, 10',
        'phone': '+79001234567',
        'comment': 'Позвонить заранее',
        'products_price': '500.00',
        'delivery_price': '150.00',
        'total_price': '650.00',
        'items': [
          {
            'product_code': 'A1',
            'name': 'Apple',
            'quantity': '2',
            'price_at_moment': '100.00',
          },
          {
            'product_code': 'B2',
            'name': 'Banana',
            'quantity': '5',
            'price_at_moment': '60.00',
          },
        ],
      };

      final order = OrderDetailModel.fromJson(json);

      expect(order.id, 55);
      expect(order.status, 'delivered');
      expect(order.statusDisplay, 'Доставлен');
      expect(order.paymentMethod, 'card');
      expect(order.address, 'ул. Ленина, 10');
      expect(order.phone, '+79001234567');
      expect(order.comment, 'Позвонить заранее');
      expect(order.productsPrice, 500.00);
      expect(order.deliveryPrice, 150.00);
      expect(order.totalPrice, 650.00);
      expect(order.items.length, 2);
      expect(order.items[0].productCode, 'A1');
      expect(order.items[1].name, 'Banana');
    });

    test('empty or null items results in empty list', () {
      final json = {
        'id': '1',
        'created_at': '2025-01-01T00:00:00Z',
        'status': 'new',
        'status_display': 'Новый',
        'payment_method': 'cash',
        'address': '',
        'phone': '',
        'comment': '',
        'products_price': '0',
        'delivery_price': '0',
        'total_price': '0',
        'items': null,
      };

      final order = OrderDetailModel.fromJson(json);

      expect(order.items, isEmpty);
    });

    test('prices parsed from strings', () {
      final json = {
        'id': '10',
        'created_at': '2025-05-01T00:00:00Z',
        'status': 'new',
        'status_display': '',
        'payment_method': '',
        'address': '',
        'phone': '',
        'comment': '',
        'products_price': '1234.56',
        'delivery_price': '200.00',
        'total_price': '1434.56',
        'items': [],
      };

      final order = OrderDetailModel.fromJson(json);

      expect(order.productsPrice, 1234.56);
      expect(order.deliveryPrice, 200.00);
      expect(order.totalPrice, 1434.56);
    });

    test('multiple items parsed correctly', () {
      final json = {
        'id': '20',
        'created_at': '2025-07-01T00:00:00Z',
        'status': 'processing',
        'status_display': 'В обработке',
        'payment_method': 'card',
        'address': 'Test',
        'phone': '123',
        'comment': '',
        'products_price': '300',
        'delivery_price': '0',
        'total_price': '300',
        'items': [
          {
            'product_code': 'X1',
            'name': 'Item X',
            'quantity': '1',
            'price_at_moment': '100',
          },
          {
            'product_code': 'Y2',
            'name': 'Item Y',
            'quantity': '2',
            'price_at_moment': '50',
          },
          {
            'product_code': 'Z3',
            'name': 'Item Z',
            'quantity': '3',
            'price_at_moment': '33.33',
          },
        ],
      };

      final order = OrderDetailModel.fromJson(json);

      expect(order.items.length, 3);
      expect(order.items[0].productCode, 'X1');
      expect(order.items[0].quantity, 1);
      expect(order.items[1].productCode, 'Y2');
      expect(order.items[1].quantity, 2);
      expect(order.items[2].productCode, 'Z3');
      expect(order.items[2].priceAtMoment, 33.33);
    });
  });
}
