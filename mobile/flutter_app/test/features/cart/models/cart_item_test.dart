import 'package:flutter_test/flutter_test.dart';
import 'package:lakshmi_market/features/cart/models/cart_item.dart';
import 'package:lakshmi_market/features/home/models/product.dart';

void main() {
  group('CartItem', () {
    final product = Product(
      id: 'P1',
      name: 'Test Product',
      price: 50.0,
      description: 'A product',
      stock: 10,
    );

    test('totalPrice equals price multiplied by quantity', () {
      final cartItem = CartItem(product: product, quantity: 3);

      expect(cartItem.totalPrice, 150.0);
    });

    test('copyWith changes quantity', () {
      final cartItem = CartItem(product: product, quantity: 2);
      final updated = cartItem.copyWith(quantity: 5);

      expect(updated.quantity, 5);
      expect(updated.product.id, 'P1');
    });

    test('copyWith without args preserves quantity', () {
      final cartItem = CartItem(product: product, quantity: 4);
      final copied = cartItem.copyWith();

      expect(copied.quantity, 4);
      expect(copied.product.id, product.id);
    });
  });
}
