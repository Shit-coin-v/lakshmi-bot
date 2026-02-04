import 'package:flutter_test/flutter_test.dart';
import 'package:lakshmi_market/features/orders/models/order_model.dart';

void main() {
  group('OrderModel', () {
    test('fromJson parses full object with all fields', () {
      final json = {
        'id': 101,
        'total_price': '1500.50',
        'status': 'processing',
        'status_display': 'В сборке',
        'items_count': 3,
        'created_at': '2025-06-15T10:30:00Z',
      };

      final order = OrderModel.fromJson(json);

      expect(order.id, 101);
      expect(order.totalPrice, 1500.50);
      expect(order.status, 'processing');
      expect(order.statusDisplay, 'В сборке');
      expect(order.itemsCount, 3);
      expect(order.createdAt, DateTime.utc(2025, 6, 15, 10, 30, 0));
    });

    test('total_price parsed from string', () {
      final json = {
        'id': 1,
        'total_price': '999.99',
        'status': 'new',
        'status_display': 'Новый',
        'items_count': 1,
        'created_at': '2025-01-01T00:00:00Z',
      };

      final order = OrderModel.fromJson(json);

      expect(order.totalPrice, 999.99);
    });

    test('missing optional fields get defaults', () {
      final json = {
        'id': 2,
        'total_price': '0',
      };

      final order = OrderModel.fromJson(json);

      expect(order.status, '');
      expect(order.statusDisplay, '');
      expect(order.itemsCount, 0);
    });

    test('invalid created_at defaults to approximately DateTime.now()', () {
      final before = DateTime.now();
      final json = {
        'id': 3,
        'total_price': '0',
        'created_at': 'not-a-date',
      };

      final order = OrderModel.fromJson(json);
      final after = DateTime.now();

      expect(order.createdAt, isNotNull);
      expect(
        order.createdAt.isAfter(before.subtract(const Duration(seconds: 1))),
        isTrue,
      );
      expect(
        order.createdAt.isBefore(after.add(const Duration(seconds: 1))),
        isTrue,
      );
    });
  });
}
