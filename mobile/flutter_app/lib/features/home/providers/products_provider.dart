import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../catalog/models/category_node.dart';
import '../../catalog/providers/catalog_provider.dart';

// Текст поискового запроса. Изменяется через debounce из HomeScreen.
final searchQueryProvider = StateProvider<String>((ref) => '');

// Путь по дереву категорий: [] = корень («Все»), [Молочные] = в Молочные,
// [Молочные, Молоко] = в Молоко. Используется CategoryStrip и
// CategoryBreadcrumbs. НЕ autoDispose — должно переживать перерисовки HomeScreen.
final categoryPathProvider = StateProvider<List<CategoryNode>>((ref) => []);

// Категории текущего уровня для отображения в полосе чипов.
// Пустой путь → корневые категории; иначе — дети последнего узла пути.
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
