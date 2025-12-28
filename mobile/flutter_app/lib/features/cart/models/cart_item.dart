import '../../home/models/product.dart';

class CartItem {
  final Product product;
  final int quantity;

  const CartItem({required this.product, required this.quantity});

  // Метод, чтобы легко менять количество (создает копию с новым кол-вом)
  CartItem copyWith({int? quantity}) {
    return CartItem(product: product, quantity: quantity ?? this.quantity);
  }

  // Цена позиции (цена товара * кол-во)
  double get totalPrice => product.price * quantity;
}
