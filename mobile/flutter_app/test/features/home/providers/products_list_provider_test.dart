import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:lakshmi_market/features/home/models/product.dart';
import 'package:lakshmi_market/features/home/providers/products_list_provider.dart';
import 'package:lakshmi_market/features/home/services/products_service.dart';

class _MockService extends Mock implements ProductsService {}

ProductPage _page(List<Product> items, {bool hasMore = false}) =>
    ProductPage(items: items, hasMore: hasMore);

Product _p(String id) =>
    Product(id: id, name: id, price: 1.0, description: '', stock: 1.0);

void main() {
  late _MockService mock;

  setUp(() {
    mock = _MockService();
    when(() => mock.getShowcase(
          search: any(named: 'search'),
          page: any(named: 'page'),
        )).thenAnswer((_) async => _page([]));
    when(() => mock.getProducts(
          search: any(named: 'search'),
          categoryId: any(named: 'categoryId'),
          page: any(named: 'page'),
        )).thenAnswer((_) async => _page([]));
  });

  ProviderContainer makeContainer() {
    final c = ProviderContainer(overrides: [
      productsServiceProvider.overrideWithValue(mock),
    ]);
    addTearDown(c.dispose);
    return c;
  }

  group('ProductsListProvider — initial build', () {
    test('empty key → calls getShowcase(page: 1)', () async {
      final c = makeContainer();
      const key = ProductsListKey(search: '', categoryId: null);

      await c.read(productsListProvider(key).future);

      verify(() => mock.getShowcase(search: '', page: 1)).called(1);
      verifyNever(() => mock.getProducts(
            search: any(named: 'search'),
            categoryId: any(named: 'categoryId'),
            page: any(named: 'page'),
          ));
    });

    test('key with search → calls getShowcase(search:, page: 1)', () async {
      final c = makeContainer();
      const key = ProductsListKey(search: 'milk', categoryId: null);

      await c.read(productsListProvider(key).future);

      verify(() => mock.getShowcase(search: 'milk', page: 1)).called(1);
    });

    test('key with categoryId → calls getProducts(categoryId:, page: 1)',
        () async {
      final c = makeContainer();
      const key = ProductsListKey(search: '', categoryId: 7);

      await c.read(productsListProvider(key).future);

      verify(() => mock.getProducts(
            search: '',
            categoryId: 7,
            page: 1,
          )).called(1);
    });

    test('build sets page=1 and isLoadingMore=false', () async {
      when(() => mock.getShowcase(
            search: any(named: 'search'),
            page: any(named: 'page'),
          )).thenAnswer((_) async => _page([_p('A'), _p('B')], hasMore: true));

      final c = makeContainer();
      const key = ProductsListKey(search: '', categoryId: null);

      final state = await c.read(productsListProvider(key).future);

      expect(state.items.length, 2);
      expect(state.page, 1);
      expect(state.hasMore, true);
      expect(state.isLoadingMore, false);
      expect(state.loadMoreError, isNull);
    });
  });

  group('ProductsListProvider — loadMore', () {
    test('appends next page items and increments page', () async {
      when(() => mock.getShowcase(
            search: any(named: 'search'),
            page: 1,
          )).thenAnswer((_) async => _page([_p('A')], hasMore: true));
      when(() => mock.getShowcase(
            search: any(named: 'search'),
            page: 2,
          )).thenAnswer((_) async => _page([_p('B')], hasMore: false));

      final c = makeContainer();
      const key = ProductsListKey(search: '', categoryId: null);
      await c.read(productsListProvider(key).future);

      await c.read(productsListProvider(key).notifier).loadMore();

      final state = c.read(productsListProvider(key)).value!;
      expect(state.items.map((p) => p.id), ['A', 'B']);
      expect(state.page, 2);
      expect(state.hasMore, false);
    });

    test('no-op when hasMore=false', () async {
      when(() => mock.getShowcase(
            search: any(named: 'search'),
            page: any(named: 'page'),
          )).thenAnswer((_) async => _page([_p('A')], hasMore: false));

      final c = makeContainer();
      const key = ProductsListKey(search: '', categoryId: null);
      await c.read(productsListProvider(key).future);

      await c.read(productsListProvider(key).notifier).loadMore();

      verify(() => mock.getShowcase(search: '', page: 1)).called(1);
      verifyNever(() => mock.getShowcase(search: '', page: 2));
    });

    test('no-op when isLoadingMore=true (race protection)', () async {
      // Page 1 — сразу
      when(() => mock.getShowcase(
            search: any(named: 'search'),
            page: 1,
          )).thenAnswer((_) async => _page([_p('A')], hasMore: true));

      // Page 2 — отложенный future, чтобы поймать «in-flight» состояние
      final completer = Completer<ProductPage>();
      when(() => mock.getShowcase(
            search: any(named: 'search'),
            page: 2,
          )).thenAnswer((_) => completer.future);

      final c = makeContainer();
      const key = ProductsListKey(search: '', categoryId: null);
      await c.read(productsListProvider(key).future);

      final notifier = c.read(productsListProvider(key).notifier);
      final fut1 = notifier.loadMore();
      final fut2 = notifier.loadMore(); // должен сразу вернуться (no-op)

      // Завершаем page 2
      completer.complete(_page([_p('B')], hasMore: false));
      await fut1;
      await fut2;

      // Сервис вызван для page 2 ровно один раз
      verify(() => mock.getShowcase(search: '', page: 2)).called(1);
    });

    test('on error sets loadMoreError, items preserved', () async {
      when(() => mock.getShowcase(
            search: any(named: 'search'),
            page: 1,
          )).thenAnswer((_) async => _page([_p('A')], hasMore: true));
      when(() => mock.getShowcase(
            search: any(named: 'search'),
            page: 2,
          )).thenThrow(Exception('boom'));

      final c = makeContainer();
      const key = ProductsListKey(search: '', categoryId: null);
      await c.read(productsListProvider(key).future);

      await c.read(productsListProvider(key).notifier).loadMore();

      final state = c.read(productsListProvider(key)).value!;
      expect(state.items.map((p) => p.id), ['A']);
      expect(state.loadMoreError, isNotNull);
      expect(state.isLoadingMore, false);
    });
  });

  group('ProductsListProvider — retryLoadMore', () {
    test('clears error and retries the same page', () async {
      var page2Calls = 0;
      when(() => mock.getShowcase(
            search: any(named: 'search'),
            page: 1,
          )).thenAnswer((_) async => _page([_p('A')], hasMore: true));
      when(() => mock.getShowcase(
            search: any(named: 'search'),
            page: 2,
          )).thenAnswer((_) async {
        page2Calls++;
        if (page2Calls == 1) throw Exception('boom');
        return _page([_p('B')], hasMore: false);
      });

      final c = makeContainer();
      const key = ProductsListKey(search: '', categoryId: null);
      await c.read(productsListProvider(key).future);
      await c.read(productsListProvider(key).notifier).loadMore();
      // первая попытка упала
      expect(c.read(productsListProvider(key)).value!.loadMoreError, isNotNull);

      await c.read(productsListProvider(key).notifier).retryLoadMore();

      final state = c.read(productsListProvider(key)).value!;
      expect(state.items.map((p) => p.id), ['A', 'B']);
      expect(state.loadMoreError, isNull);
      expect(state.page, 2);
    });
  });

  group('ProductsListProvider — refresh', () {
    test('re-runs build from page 1', () async {
      var page1Calls = 0;
      when(() => mock.getShowcase(
            search: any(named: 'search'),
            page: 1,
          )).thenAnswer((_) async {
        page1Calls++;
        return _page([_p('A$page1Calls')], hasMore: false);
      });

      final c = makeContainer();
      const key = ProductsListKey(search: '', categoryId: null);
      await c.read(productsListProvider(key).future);
      expect(c.read(productsListProvider(key)).value!.items.first.id, 'A1');

      await c.read(productsListProvider(key).notifier).refresh();

      expect(c.read(productsListProvider(key)).value!.items.first.id, 'A2');
      expect(page1Calls, 2);
    });
  });

  group('ProductsListKey equality', () {
    test('same search and categoryId → equal and same hashCode', () {
      const k1 = ProductsListKey(search: 'milk', categoryId: 7);
      const k2 = ProductsListKey(search: 'milk', categoryId: 7);
      expect(k1, k2);
      expect(k1.hashCode, k2.hashCode);
    });

    test('different categoryId → not equal', () {
      const k1 = ProductsListKey(search: '', categoryId: 7);
      const k2 = ProductsListKey(search: '', categoryId: 8);
      expect(k1 == k2, false);
    });
  });
}
