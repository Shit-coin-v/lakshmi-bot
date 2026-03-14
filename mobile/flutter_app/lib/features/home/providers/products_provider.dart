import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/products_service.dart';
import '../models/product.dart';

// 1. Provider for search query state
final searchQueryProvider = StateProvider<String>((ref) => '');

// 2. Showcase provider — витрина главной страницы (предрассчитанный ranking)
final productsProvider = FutureProvider.autoDispose<List<Product>>((ref) async {
  final search = ref.watch(searchQueryProvider);

  final service = ref.read(productsServiceProvider);

  return service.getShowcase(search: search);
});

// 3. Products by category provider (cached for 5 minutes)
final categoryProductsProvider =
    FutureProvider.autoDispose.family<List<Product>, int>((ref, categoryId) async {
  final link = ref.keepAlive();

  // Автоматически освобождаем через 5 минут после ухода с экрана
  Timer? timer;
  ref.onDispose(() => timer?.cancel());
  ref.onCancel(() {
    timer = Timer(const Duration(minutes: 5), link.close);
  });
  ref.onResume(() {
    timer?.cancel();
  });

  final service = ref.read(productsServiceProvider);
  return service.getProducts(categoryId: categoryId);
});
