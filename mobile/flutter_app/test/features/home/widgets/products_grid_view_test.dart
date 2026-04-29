import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:lakshmi_market/features/home/models/product.dart';
import 'package:lakshmi_market/features/home/providers/products_list_provider.dart';
import 'package:lakshmi_market/features/home/services/products_service.dart';
import 'package:lakshmi_market/features/home/widgets/products_grid_view.dart';

class _MockService extends Mock implements ProductsService {}

Product _p(String id) =>
    Product(id: id, name: id, price: 1.0, description: '', stock: 1.0);

ProductPage _page(List<Product> items, {bool hasMore = false}) =>
    ProductPage(items: items, hasMore: hasMore);

Widget _wrap({
  required _MockService service,
  required Widget child,
}) =>
    ProviderScope(
      overrides: [productsServiceProvider.overrideWithValue(service)],
      child: MaterialApp(home: Scaffold(body: child)),
    );

void main() {
  late _MockService service;
  const key = ProductsListKey(search: '', categoryId: null);

  setUp(() {
    service = _MockService();
    when(() => service.getShowcase(
          search: any(named: 'search'),
          page: any(named: 'page'),
        )).thenAnswer((_) async => _page([]));
  });

  testWidgets('shows CircularProgressIndicator on first load', (tester) async {
    when(() => service.getShowcase(
          search: any(named: 'search'),
          page: any(named: 'page'),
        )).thenAnswer((_) async {
      await Future.delayed(const Duration(seconds: 1));
      return _page([]);
    });

    await tester.pumpWidget(
      _wrap(service: service, child: const ProductsGridView(listKey: key)),
    );
    await tester.pump(); // не settle — остаёмся на loading

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    await tester.pump(const Duration(seconds: 2)); // дрейним таймер
  });

  testWidgets('shows products in grid when data is loaded', (tester) async {
    when(() => service.getShowcase(
          search: any(named: 'search'),
          page: any(named: 'page'),
        )).thenAnswer((_) async => _page([_p('A'), _p('B'), _p('C')]));

    await tester.pumpWidget(
      _wrap(service: service, child: const ProductsGridView(listKey: key)),
    );
    await tester.pumpAndSettle();

    // A и B попадают в видимую область; C — во второй ряд, может быть
    // за пределами тестового вьюпорта, поэтому skipOffstage: false.
    expect(find.text('A', skipOffstage: false), findsOneWidget);
    expect(find.text('B', skipOffstage: false), findsOneWidget);
    expect(find.text('C', skipOffstage: false), findsOneWidget);
  });

  testWidgets('shows empty state when no products', (tester) async {
    await tester.pumpWidget(
      _wrap(service: service, child: const ProductsGridView(listKey: key)),
    );
    await tester.pumpAndSettle();

    expect(find.text('Ничего не найдено'), findsOneWidget);
  });

  testWidgets('shows footer spinner when isLoadingMore=true', (tester) async {
    when(() => service.getShowcase(
          search: any(named: 'search'),
          page: 1,
        )).thenAnswer((_) async => _page([_p('A')], hasMore: true));
    when(() => service.getShowcase(
          search: any(named: 'search'),
          page: 2,
        )).thenAnswer((_) async {
      await Future.delayed(const Duration(seconds: 1));
      return _page([_p('B')]);
    });

    late WidgetRef capturedRef;
    await tester.pumpWidget(_wrap(
      service: service,
      child: Consumer(builder: (context, ref, _) {
        capturedRef = ref;
        return const ProductsGridView(listKey: key);
      }),
    ));
    await tester.pumpAndSettle();

    // Триггерим loadMore вручную, чтобы не зависеть от точной геометрии скролла.
    capturedRef.read(productsListProvider(key).notifier).loadMore();
    await tester.pump();

    // Спиннер находится в footer (SliverToBoxAdapter) ниже контента —
    // может оказаться за пределами тестового вьюпорта.
    expect(
      find.byType(CircularProgressIndicator, skipOffstage: false),
      findsOneWidget,
    );

    await tester.pump(const Duration(seconds: 2)); // драиним
  });

  testWidgets('shows retry button on loadMoreError', (tester) async {
    when(() => service.getShowcase(
          search: any(named: 'search'),
          page: 1,
        )).thenAnswer((_) async => _page([_p('A')], hasMore: true));
    when(() => service.getShowcase(
          search: any(named: 'search'),
          page: 2,
        )).thenThrow(Exception('boom'));

    late WidgetRef capturedRef;
    await tester.pumpWidget(_wrap(
      service: service,
      child: Consumer(builder: (context, ref, _) {
        capturedRef = ref;
        return const ProductsGridView(listKey: key);
      }),
    ));
    await tester.pumpAndSettle();

    await capturedRef.read(productsListProvider(key).notifier).loadMore();
    await tester.pump();

    // Footer находится ниже контента и может быть за пределами вьюпорта.
    expect(
      find.text('Не удалось загрузить', skipOffstage: false),
      findsOneWidget,
    );
    expect(find.text('Повторить', skipOffstage: false), findsOneWidget);
  });

  testWidgets('refresh triggers fetch from page 1', (tester) async {
    var calls = 0;
    when(() => service.getShowcase(
          search: any(named: 'search'),
          page: any(named: 'page'),
        )).thenAnswer((_) async {
      calls++;
      return _page([_p('A$calls')]);
    });

    late WidgetRef capturedRef;
    await tester.pumpWidget(_wrap(
      service: service,
      child: Consumer(builder: (context, ref, _) {
        capturedRef = ref;
        return const ProductsGridView(listKey: key);
      }),
    ));
    await tester.pumpAndSettle();

    expect(calls, 1);

    await capturedRef.read(productsListProvider(key).notifier).refresh();
    await tester.pumpAndSettle();

    expect(calls, 2);
  });
}
