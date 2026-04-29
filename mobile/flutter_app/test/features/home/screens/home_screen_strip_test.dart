import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';

import 'package:lakshmi_market/features/home/screens/home_screen.dart';
import 'package:lakshmi_market/features/home/services/products_service.dart';
import 'package:lakshmi_market/features/home/providers/products_provider.dart';
import 'package:lakshmi_market/features/home/widgets/category_strip.dart';
import 'package:lakshmi_market/features/home/widgets/category_breadcrumbs.dart';
import 'package:lakshmi_market/features/catalog/models/category_node.dart';
import 'package:lakshmi_market/features/catalog/providers/catalog_provider.dart';
import 'package:lakshmi_market/features/notifications/providers/notifications_provider.dart';
import 'package:lakshmi_market/features/notifications/services/notifications_api_service.dart';

class _MockProductsService extends Mock implements ProductsService {}

class _MockNotificationsApiService extends Mock
    implements NotificationsApiService {}

CategoryNode _n(int id, String name, {bool hasChildren = true}) =>
    CategoryNode(id: id, name: name, hasChildren: hasChildren);

GoRouter _testRouter() => GoRouter(
      initialLocation: '/home',
      routes: [
        GoRoute(path: '/home', builder: (_, _) => const HomeScreen()),
        GoRoute(
            path: '/home/categories',
            builder: (_, _) =>
                const Scaffold(body: Text('CATEGORIES_SCREEN'))),
        GoRoute(
            path: '/home/notifications',
            builder: (_, _) => const Scaffold(body: Text('NOTIF'))),
        GoRoute(
            path: '/home/cart',
            builder: (_, _) => const Scaffold(body: Text('CART'))),
      ],
    );

Widget _app({required List<Override> overrides}) => ProviderScope(
      overrides: overrides,
      child: MaterialApp.router(routerConfig: _testRouter()),
    );

void main() {
  late _MockProductsService mockService;

  late _MockNotificationsApiService mockNotifApi;

  setUp(() {
    mockService = _MockProductsService();
    mockNotifApi = _MockNotificationsApiService();
    when(() => mockService.getShowcase(
          search: any(named: 'search'),
          page: any(named: 'page'),
        )).thenAnswer((_) async => const ProductPage(items: [], hasMore: false));
    when(() => mockService.getProducts(
          search: any(named: 'search'),
          categoryId: any(named: 'categoryId'),
          page: any(named: 'page'),
        )).thenAnswer((_) async => const ProductPage(items: [], hasMore: false));
    // fetchNotifications никогда не вызовется без токена, но fallback на случай
    // если в будущем тест-среда изменится.
    when(() => mockNotifApi.fetchNotifications())
        .thenAnswer((_) async => []);
  });

  // NotificationsNotifier._initLoad() не вызывает loadNotifications() при
  // отсутствии bearer-токена (ApiClient().hasAccessToken == false).
  // Поэтому достаточно переопределить сервис и не касаться ApiClient.
  List<Override> baseOverrides() => [
        productsServiceProvider.overrideWithValue(mockService),
        rootCategoriesProvider.overrideWith((ref) async => [_n(1, 'Молочные')]),
        notificationsApiServiceProvider.overrideWithValue(mockNotifApi),
      ];

  testWidgets('HomeScreen renders CategoryStrip and no breadcrumbs at root',
      (tester) async {
    await tester.pumpWidget(_app(overrides: baseOverrides()));
    await tester.pumpAndSettle();

    expect(find.byType(CategoryStrip), findsOneWidget);
    expect(find.byType(CategoryBreadcrumbs), findsOneWidget);
    expect(find.text('Все'), findsOneWidget);
    // Крошки не отрисовались (при пустом пути виджет рендерит SizedBox.shrink).
    // Доказательство — отсутствие сепаратора '›' где-либо.
    expect(find.text('›'), findsNothing);
  });

  testWidgets('typing into search resets non-empty categoryPath to root',
      (tester) async {
    late ProviderContainer container;
    await tester.pumpWidget(ProviderScope(
      overrides: [
        productsServiceProvider.overrideWithValue(mockService),
        rootCategoriesProvider.overrideWith((ref) async => [_n(1, 'Молочные')]),
        notificationsApiServiceProvider.overrideWithValue(mockNotifApi),
        categoryPathProvider.overrideWith((ref) => [_n(1, 'Молочные')]),
      ],
      child: Builder(builder: (context) {
        container = ProviderScope.containerOf(context);
        return MaterialApp.router(routerConfig: _testRouter());
      }),
    ));
    await tester.pumpAndSettle();

    expect(container.read(categoryPathProvider), hasLength(1));

    await tester.enterText(find.byType(TextField), 'milk');
    // Дебаунс на 300мс — ждём.
    await tester.pump(const Duration(milliseconds: 350));

    expect(container.read(categoryPathProvider), isEmpty);
  });

  testWidgets('catalog button tap navigates to /home/categories',
      (tester) async {
    await tester.pumpWidget(_app(overrides: [
      productsServiceProvider.overrideWithValue(mockService),
      rootCategoriesProvider.overrideWith((ref) async => []),
      notificationsApiServiceProvider.overrideWithValue(mockNotifApi),
    ]));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.category_outlined));
    await tester.pumpAndSettle();

    expect(find.text('CATEGORIES_SCREEN'), findsOneWidget);
  });
}
