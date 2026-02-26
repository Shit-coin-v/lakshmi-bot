import '../../home/models/product.dart';

class CartItem {
  final Product product;
  final int quantity;

  const CartItem({required this.product, required this.quantity});

  // Method to easily change quantity (creates copy with new quantity)
  CartItem copyWith({int? quantity}) {
    return CartItem(product: product, quantity: quantity ?? this.quantity);
  }

  // Line total (product price * quantity)
  double get totalPrice => product.price * quantity;
}
