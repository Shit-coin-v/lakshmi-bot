import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/products_service.dart';
import '../models/product.dart';
import '../../catalog/models/category_node.dart';
import '../../catalog/providers/catalog_provider.dart';

// 1. Provider for search query state
final searchQueryProvider = StateProvider<String>((ref) => '');

// 2. Showcase provider — витрина главной страницы (предрассчитанный ranking).
//    Оставлен для обратной совместимости. Главная использует currentProductsProvider.
final productsProvider = FutureProvider.autoDispose<List<Product>>((ref) async {
  final search = ref.watch(searchQueryProvider);

  final service = ref.read(productsServiceProvider);

  return (await service.getShowcase(search: search)).items;
});

// 3. Products by category provider (cached for 5 minutes).
final categoryProductsProvider =
    FutureProvider.autoDispose.family<List<Product>, int>((ref, categoryId) async {
  final link = ref.keepAlive();

  // Автоматически освобождаем через 5 минут после ухода с экрана.
  Timer? timer;
  ref.onDispose(() => timer?.cancel());
  ref.onCancel(() {
    timer = Timer(const Duration(minutes: 5), link.close);
  });
  ref.onResume(() {
    timer?.cancel();
  });

  final service = ref.read(productsServiceProvider);
  return (await service.getProducts(categoryId: categoryId)).items;
});

// 4. Путь по дереву категорий: [] = «Все» (корень), [Молочные] = в Молочные,
//    [Молочные, Молоко] = в Молоко. Используется для drill-down полосы чипов.
//    НЕ autoDispose — должно переживать перерисовки HomeScreen.
final categoryPathProvider = StateProvider<List<CategoryNode>>((ref) => []);

// 5. Категории текущего уровня (для отображения в полосе чипов).
//    Пустой путь → корневые категории; иначе — дети последнего узла пути.
final currentLevelCategoriesProvider =
    FutureProvider.autoDispose<List<CategoryNode>>((ref) async {
  final path = ref.watch(categoryPathProvider);
  if (path.isEmpty) {
    return ref.watch(rootCategoriesProvider.future);
  }
  final last = path.last;
  if (!last.hasChildren) {
    return <CategoryNode>[];
  }
  return ref.watch(childCategoriesProvider(last.id).future);
});

// 6. Товары для отображения в сетке. Логика:
//    • search непустой → витрина с поиском (глобально по каталогу);
//    • путь пуст → витрина без аргументов;
//    • путь не пуст → товары категории и всего поддерева (бэк делает BFS).
final currentProductsProvider =
    FutureProvider.autoDispose<List<Product>>((ref) async {
  final search = ref.watch(searchQueryProvider);
  final path = ref.watch(categoryPathProvider);
  final service = ref.read(productsServiceProvider);

  if (search.isNotEmpty) {
    return (await service.getShowcase(search: search)).items;
  }
  if (path.isEmpty) {
    return (await service.getShowcase()).items;
  }
  return (await service.getProducts(categoryId: path.last.id)).items;
});
