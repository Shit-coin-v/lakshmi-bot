import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/product.dart';
import '../services/products_service.dart';

// FutureProvider автоматически обрабатывает 3 состояния:
// 1. loading (грузится)
// 2. data (данные пришли)
// 3. error (ошибка)
final productsProvider = FutureProvider.autoDispose<List<Product>>((ref) async {
  final service = ref.watch(productsServiceProvider);
  return service.fetchProducts();
});
