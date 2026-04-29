import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:lakshmi_market/features/home/widgets/category_strip.dart';
import 'package:lakshmi_market/features/home/providers/products_provider.dart';
import 'package:lakshmi_market/features/catalog/models/category_node.dart';
import 'package:lakshmi_market/features/catalog/providers/catalog_provider.dart';

CategoryNode _n(int id, String name, {bool hasChildren = true}) =>
    CategoryNode(id: id, name: name, hasChildren: hasChildren);

Widget _wrap({
  required List<Override> overrides,
  Widget? child,
}) =>
    ProviderScope(
      overrides: overrides,
      child: MaterialApp(home: Scaffold(body: child ?? const CategoryStrip())),
    );

void main() {
  group('CategoryStrip — root level', () {
    testWidgets('shows "Все" chip active and root categories as inactive chips',
        (tester) async {
      await tester.pumpWidget(_wrap(
        overrides: [
          rootCategoriesProvider.overrideWith((ref) async => [
                _n(1, 'Молочные'),
                _n(2, 'Хлеб'),
              ]),
        ],
      ));
      await tester.pumpAndSettle();

      expect(find.text('Все'), findsOneWidget);
      expect(find.text('Молочные'), findsOneWidget);
      expect(find.text('Хлеб'), findsOneWidget);
      expect(find.byIcon(Icons.arrow_back), findsNothing);
    });

    testWidgets('tap on category chip pushes it to categoryPathProvider',
        (tester) async {
      late ProviderContainer container;
      await tester.pumpWidget(ProviderScope(
        overrides: [
          rootCategoriesProvider.overrideWith((ref) async => [_n(1, 'Молочные')]),
        ],
        child: Builder(builder: (context) {
          container = ProviderScope.containerOf(context);
          return const MaterialApp(home: Scaffold(body: CategoryStrip()));
        }),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Молочные'));
      await tester.pump();

      final path = container.read(categoryPathProvider);
      expect(path, hasLength(1));
      expect(path.first.id, 1);
    });
  });

  group('CategoryStrip — nested level', () {
    testWidgets('shows back arrow chip and active current chip',
        (tester) async {
      await tester.pumpWidget(_wrap(
        overrides: [
          categoryPathProvider.overrideWith((ref) => [_n(1, 'Молочные')]),
          childCategoriesProvider(1).overrideWith((ref) async => [
                _n(11, 'Молоко'),
                _n(12, 'Йогурты'),
              ]),
        ],
      ));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.arrow_back), findsOneWidget);
      expect(find.text('Все'), findsNothing);
      expect(find.text('Молочные'), findsOneWidget); // активный
      expect(find.text('Молоко'), findsOneWidget);
      expect(find.text('Йогурты'), findsOneWidget);
    });

    testWidgets('tap on back arrow pops one level off the path',
        (tester) async {
      late ProviderContainer container;
      await tester.pumpWidget(ProviderScope(
        overrides: [
          categoryPathProvider.overrideWith((ref) => [_n(1, 'Молочные'), _n(11, 'Молоко')]),
          childCategoriesProvider(11).overrideWith((ref) async => []),
        ],
        child: Builder(builder: (context) {
          container = ProviderScope.containerOf(context);
          return const MaterialApp(home: Scaffold(body: CategoryStrip()));
        }),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.arrow_back));
      await tester.pump();

      final path = container.read(categoryPathProvider);
      expect(path, hasLength(1));
      expect(path.first.id, 1);
    });

    testWidgets('tap on already-active chip does nothing', (tester) async {
      late ProviderContainer container;
      await tester.pumpWidget(ProviderScope(
        overrides: [
          categoryPathProvider.overrideWith((ref) => [_n(1, 'Молочные')]),
          childCategoriesProvider(1).overrideWith((ref) async => [_n(11, 'Молоко')]),
        ],
        child: Builder(builder: (context) {
          container = ProviderScope.containerOf(context);
          return const MaterialApp(home: Scaffold(body: CategoryStrip()));
        }),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Молочные'));
      await tester.pump();

      final path = container.read(categoryPathProvider);
      expect(path, hasLength(1));
      expect(path.first.id, 1); // не изменилось
    });
  });

  group('CategoryStrip — loading and error states', () {
    testWidgets('shows skeleton chips while loading', (tester) async {
      await tester.pumpWidget(_wrap(
        overrides: [
          rootCategoriesProvider.overrideWith((ref) async {
            await Future.delayed(const Duration(seconds: 1));
            return <CategoryNode>[];
          }),
        ],
      ));
      await tester.pump(); // не settle — остаёмся в loading

      expect(find.byKey(const ValueKey('category-skeleton')), findsWidgets);
      await tester.pump(const Duration(seconds: 2)); // дрейним таймер
    });

    testWidgets('shows error message and retry on error', (tester) async {
      await tester.pumpWidget(_wrap(
        overrides: [
          rootCategoriesProvider.overrideWith((ref) async => throw Exception('boom')),
        ],
      ));
      await tester.pumpAndSettle();

      expect(find.textContaining('Не удалось загрузить'), findsOneWidget);
      expect(find.text('Повторить'), findsOneWidget);
    });
  });
}
