import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../home/models/product.dart';
import '../models/cart_item.dart';

// Global access to cart state
final cartProvider = StateNotifierProvider<CartNotifier, List<CartItem>>((ref) {
  return CartNotifier();
});

// Provider for calculating total price (watches cart state)
final cartTotalProvider = Provider<double>((ref) {
  final cartItems = ref.watch(cartProvider);
  return cartItems.fold(0, (sum, item) => sum + item.totalPrice);
});

// Provider for counting items (for cart badge)
final cartCountProvider = Provider<int>((ref) {
  final cartItems = ref.watch(cartProvider);
  return cartItems.fold(0, (sum, item) => sum + item.quantity);
});

class CartNotifier extends StateNotifier<List<CartItem>> {
  CartNotifier() : super([]);

  // Add product (or increase quantity)
  void addProduct(Product product) {
    // Check if product already exists in cart
    final index = state.indexWhere((item) => item.product.id == product.id);

    if (index != -1) {
      // If exists — increase quantity
      final oldItem = state[index];
      // Copy list so Riverpod detects the change
      final newState = [...state];
      newState[index] = oldItem.copyWith(quantity: oldItem.quantity + 1);
      state = newState;
    } else {
      // If not — add new item
      state = [...state, CartItem(product: product, quantity: 1)];
    }
  }

  // Decrease quantity
  void removeProduct(Product product) {
    final index = state.indexWhere((item) => item.product.id == product.id);

    if (index != -1) {
      final oldItem = state[index];
      if (oldItem.quantity > 1) {
        // Decrease by 1
        final newState = [...state];
        newState[index] = oldItem.copyWith(quantity: oldItem.quantity - 1);
        state = newState;
      } else {
        // If was 1, remove entirely
        state = [
          for (final item in state)
            if (item.product.id != product.id) item,
        ];
      }
    }
  }

  // Clear cart (after order)
  void clear() {
    state = [];
  }
}
