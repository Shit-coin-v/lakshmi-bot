import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:lakshmi_market/features/catalog/models/category_node.dart';
import 'package:lakshmi_market/features/catalog/providers/catalog_provider.dart';
import 'package:lakshmi_market/features/home/providers/products_provider.dart';

CategoryNode _node(int id, {bool hasChildren = true}) =>
    CategoryNode(id: id, name: 'Cat $id', hasChildren: hasChildren);

void main() {
  group('categoryPathProvider', () {
    test('initial state is empty list', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      expect(container.read(categoryPathProvider), isEmpty);
    });
  });

  group('currentLevelCategoriesProvider', () {
    test('empty path → returns rootCategoriesProvider data', () async {
      final roots = [_node(1), _node(2)];
      final container = ProviderContainer(overrides: [
        rootCategoriesProvider.overrideWith((ref) async => roots),
      ]);
      addTearDown(container.dispose);

      final result = await container.read(currentLevelCategoriesProvider.future);
      expect(result, roots);
    });

    test('non-empty path with hasChildren=true → reads childCategoriesProvider',
        () async {
      final children = [_node(11), _node(12)];
      final container = ProviderContainer(overrides: [
        childCategoriesProvider(7).overrideWith((ref) async => children),
      ]);
      addTearDown(container.dispose);

      container.read(categoryPathProvider.notifier).state =
          [_node(7, hasChildren: true)];

      final result = await container.read(currentLevelCategoriesProvider.future);
      expect(result, children);
    });

    test('non-empty path with hasChildren=false → returns empty list', () async {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(categoryPathProvider.notifier).state =
          [_node(7, hasChildren: false)];

      final result = await container.read(currentLevelCategoriesProvider.future);
      expect(result, isEmpty);
    });
  });
}
