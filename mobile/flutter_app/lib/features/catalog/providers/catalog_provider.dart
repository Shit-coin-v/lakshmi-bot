import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/category_node.dart';
import '../services/catalog_service.dart';

final rootCategoriesProvider =
    FutureProvider.autoDispose<List<CategoryNode>>((ref) async {
  final service = ref.read(catalogServiceProvider);
  return service.getRootCategories();
});

final childCategoriesProvider =
    FutureProvider.autoDispose.family<List<CategoryNode>, int>((ref, parentId) async {
  final service = ref.read(catalogServiceProvider);
  return service.getChildren(parentId);
});
