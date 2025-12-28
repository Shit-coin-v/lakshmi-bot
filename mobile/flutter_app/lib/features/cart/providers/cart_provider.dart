import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../home/models/product.dart';
import '../models/cart_item.dart';

// Глобальный доступ к корзине
final cartProvider = StateNotifierProvider<CartNotifier, List<CartItem>>((ref) {
  return CartNotifier();
});

// Провайдер для подсчета итоговой суммы (читает состояние корзины)
final cartTotalProvider = Provider<double>((ref) {
  final cartItems = ref.watch(cartProvider);
  return cartItems.fold(0, (sum, item) => sum + item.totalPrice);
});

// Провайдер для подсчета кол-ва товаров (для значка на корзине)
final cartCountProvider = Provider<int>((ref) {
  final cartItems = ref.watch(cartProvider);
  return cartItems.fold(0, (sum, item) => sum + item.quantity);
});

class CartNotifier extends StateNotifier<List<CartItem>> {
  CartNotifier() : super([]);

  // Добавить товар (или увеличить количество)
  void addProduct(Product product) {
    // Проверяем, есть ли уже этот товар в корзине
    final index = state.indexWhere((item) => item.product.id == product.id);

    if (index != -1) {
      // Если есть - увеличиваем количество
      final oldItem = state[index];
      // Делаем копию списка, чтобы Riverpod увидел изменение
      final newState = [...state];
      newState[index] = oldItem.copyWith(quantity: oldItem.quantity + 1);
      state = newState;
    } else {
      // Если нет - добавляем новый
      state = [...state, CartItem(product: product, quantity: 1)];
    }
  }

  // Уменьшить количество
  void removeProduct(Product product) {
    final index = state.indexWhere((item) => item.product.id == product.id);

    if (index != -1) {
      final oldItem = state[index];
      if (oldItem.quantity > 1) {
        // Уменьшаем на 1
        final newState = [...state];
        newState[index] = oldItem.copyWith(quantity: oldItem.quantity - 1);
        state = newState;
      } else {
        // Если было 1, то удаляем совсем
        state = [
          for (final item in state)
            if (item.product.id != product.id) item,
        ];
      }
    }
  }

  // Очистить корзину (после заказа)
  void clear() {
    state = [];
  }
}
