import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:lakshmi_market/features/home/providers/products_provider.dart';
import 'package:lakshmi_market/features/home/services/products_service.dart';
import 'package:lakshmi_market/features/home/models/product.dart';
import 'package:lakshmi_market/features/catalog/models/category_node.dart';
import 'package:lakshmi_market/features/catalog/providers/catalog_provider.dart';

class MockProductsService extends Mock implements ProductsService {}

CategoryNode _node(int id, {bool hasChildren = true}) =>
    CategoryNode(id: id, name: 'Cat $id', hasChildren: hasChildren);

void main() {
  late MockProductsService mockService;

  setUp(() {
    mockService = MockProductsService();
    when(() => mockService.getShowcase(search: any(named: 'search')))
        .thenAnswer((_) async => <Product>[]);
    when(() => mockService.getProducts(
          search: any(named: 'search'),
          categoryId: any(named: 'categoryId'),
        )).thenAnswer((_) async => <Product>[]);
  });

  group('categoryPathProvider', () {
    test('initial state is empty list', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      expect(container.read(categoryPathProvider), isEmpty);
    });
  });

  group('currentProductsProvider', () {
    test('empty path + empty search → calls getShowcase()', () async {
      final container = ProviderContainer(overrides: [
        productsServiceProvider.overrideWithValue(mockService),
      ]);
      addTearDown(container.dispose);

      await container.read(currentProductsProvider.future);

      verify(() => mockService.getShowcase(search: '')).called(1);
      verifyNever(() => mockService.getProducts(
            search: any(named: 'search'),
            categoryId: any(named: 'categoryId'),
          ));
    });

    test('non-empty search → calls getShowcase(search: q) regardless of path',
        () async {
      final container = ProviderContainer(overrides: [
        productsServiceProvider.overrideWithValue(mockService),
      ]);
      addTearDown(container.dispose);

      container.read(categoryPathProvider.notifier).state = [_node(10)];
      container.read(searchQueryProvider.notifier).state = 'milk';

      await container.read(currentProductsProvider.future);

      verify(() => mockService.getShowcase(search: 'milk')).called(1);
      verifyNever(() => mockService.getProducts(
            search: any(named: 'search'),
            categoryId: any(named: 'categoryId'),
          ));
    });

    test('non-empty path + empty search → calls getProducts(categoryId: last.id)',
        () async {
      final container = ProviderContainer(overrides: [
        productsServiceProvider.overrideWithValue(mockService),
      ]);
      addTearDown(container.dispose);

      container.read(categoryPathProvider.notifier).state = [_node(10), _node(25)];

      await container.read(currentProductsProvider.future);

      verify(() => mockService.getProducts(categoryId: 25)).called(1);
      verifyNever(() => mockService.getShowcase(search: any(named: 'search')));
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

      container.read(categoryPathProvider.notifier).state = [_node(7, hasChildren: true)];

      final result = await container.read(currentLevelCategoriesProvider.future);
      expect(result, children);
    });

    test('non-empty path with hasChildren=false → returns empty list', () async {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(categoryPathProvider.notifier).state = [_node(7, hasChildren: false)];

      final result = await container.read(currentLevelCategoriesProvider.future);
      expect(result, isEmpty);
    });
  });
}
