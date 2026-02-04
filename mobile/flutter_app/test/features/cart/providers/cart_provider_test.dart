import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lakshmi_market/features/cart/models/cart_item.dart';
import 'package:lakshmi_market/features/cart/providers/cart_provider.dart';
import 'package:lakshmi_market/features/home/models/product.dart';

Product _makeProduct({
  String id = 'P1',
  String name = 'Test',
  double price = 10.0,
}) =>
    Product(id: id, name: name, price: price, description: '', stock: 10);

void main() {
  group('CartNotifier', () {
    late CartNotifier notifier;

    setUp(() {
      notifier = CartNotifier();
    });

    test('initial state is empty', () {
      expect(notifier.debugState, isEmpty);
    });

    test('addProduct adds new item with quantity 1', () {
      final product = _makeProduct();
      notifier.addProduct(product);

      expect(notifier.debugState, hasLength(1));
      expect(notifier.debugState.first.product.id, 'P1');
      expect(notifier.debugState.first.quantity, 1);
    });

    test('addProduct same product again increments quantity', () {
      final product = _makeProduct();
      notifier.addProduct(product);
      notifier.addProduct(product);

      expect(notifier.debugState, hasLength(1));
      expect(notifier.debugState.first.quantity, 2);
    });

    test('addProduct different products are separate items', () {
      notifier.addProduct(_makeProduct(id: 'P1', name: 'Apple'));
      notifier.addProduct(_makeProduct(id: 'P2', name: 'Banana'));

      expect(notifier.debugState, hasLength(2));
      expect(notifier.debugState[0].product.id, 'P1');
      expect(notifier.debugState[1].product.id, 'P2');
    });

    test('removeProduct decrements quantity', () {
      final product = _makeProduct();
      notifier.addProduct(product);
      notifier.addProduct(product); // qty=2
      notifier.removeProduct(product);

      expect(notifier.debugState, hasLength(1));
      expect(notifier.debugState.first.quantity, 1);
    });

    test('removeProduct removes item when quantity reaches 0', () {
      final product = _makeProduct();
      notifier.addProduct(product); // qty=1
      notifier.removeProduct(product); // qty=0 -> removed

      expect(notifier.debugState, isEmpty);
    });

    test('removeProduct on non-existent product does nothing', () {
      notifier.addProduct(_makeProduct(id: 'P1'));
      notifier.removeProduct(_makeProduct(id: 'P999'));

      expect(notifier.debugState, hasLength(1));
      expect(notifier.debugState.first.product.id, 'P1');
    });

    test('clear empties the cart', () {
      notifier.addProduct(_makeProduct(id: 'P1'));
      notifier.addProduct(_makeProduct(id: 'P2'));
      notifier.clear();

      expect(notifier.debugState, isEmpty);
    });
  });

  group('Derived providers', () {
    test('cartTotalProvider and cartCountProvider compute correctly', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(cartProvider.notifier);
      notifier.addProduct(_makeProduct(price: 10.0));
      notifier.addProduct(_makeProduct(price: 10.0)); // qty=2

      expect(container.read(cartTotalProvider), 20.0);
      expect(container.read(cartCountProvider), 2);
    });
  });
}
