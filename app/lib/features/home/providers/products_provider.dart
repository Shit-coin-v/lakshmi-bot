import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/products_service.dart';
import '../models/product.dart';

// 1. Провайдер для хранения строки поиска
final searchQueryProvider = StateProvider<String>((ref) => '');

// 2. Провайдер товаров (перезапускается при изменении поиска)
final productsProvider = FutureProvider.autoDispose<List<Product>>((ref) async {
  final search = ref.watch(searchQueryProvider);

  final service = ref.read(productsServiceProvider);

  return service.getProducts(search: search);
});
