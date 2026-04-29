import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:lakshmi_market/features/home/widgets/category_breadcrumbs.dart';
import 'package:lakshmi_market/features/home/providers/products_provider.dart';
import 'package:lakshmi_market/features/catalog/models/category_node.dart';

CategoryNode _n(int id, String name) =>
    CategoryNode(id: id, name: name, hasChildren: true);

Widget _wrap({required List<Override> overrides}) => ProviderScope(
      overrides: overrides,
      child: const MaterialApp(
        home: Scaffold(body: CategoryBreadcrumbs()),
      ),
    );

void main() {
  group('CategoryBreadcrumbs', () {
    testWidgets('renders nothing when path is empty', (tester) async {
      await tester.pumpWidget(_wrap(overrides: []));
      await tester.pumpAndSettle();

      expect(find.text('Все'), findsNothing);
      expect(find.byType(SizedBox), findsWidgets); // пустышка
    });

    testWidgets('renders "Все › X" for path of length 1', (tester) async {
      await tester.pumpWidget(_wrap(overrides: [
        categoryPathProvider.overrideWith((ref) => [_n(1, 'Молочные')]),
      ]));
      await tester.pumpAndSettle();

      expect(find.text('Все'), findsOneWidget);
      expect(find.text('Молочные'), findsOneWidget);
    });

    testWidgets('renders "Все › X › Y" for path of length 2', (tester) async {
      await tester.pumpWidget(_wrap(overrides: [
        categoryPathProvider.overrideWith((ref) => [_n(1, 'Молочные'), _n(11, 'Молоко')]),
      ]));
      await tester.pumpAndSettle();

      expect(find.text('Все'), findsOneWidget);
      expect(find.text('Молочные'), findsOneWidget);
      expect(find.text('Молоко'), findsOneWidget);
    });

    testWidgets('tap on "Все" empties the path', (tester) async {
      late ProviderContainer container;
      await tester.pumpWidget(ProviderScope(
        overrides: [
          categoryPathProvider.overrideWith((ref) => [_n(1, 'Молочные')]),
        ],
        child: Builder(builder: (context) {
          container = ProviderScope.containerOf(context);
          return const MaterialApp(home: Scaffold(body: CategoryBreadcrumbs()));
        }),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Все'));
      await tester.pump();

      expect(container.read(categoryPathProvider), isEmpty);
    });

    testWidgets('tap on intermediate level truncates the path to that level',
        (tester) async {
      late ProviderContainer container;
      await tester.pumpWidget(ProviderScope(
        overrides: [
          categoryPathProvider.overrideWith((ref) => [
                _n(1, 'Молочные'),
                _n(11, 'Молоко'),
                _n(111, 'Молоко 1л'),
              ]),
        ],
        child: Builder(builder: (context) {
          container = ProviderScope.containerOf(context);
          return const MaterialApp(home: Scaffold(body: CategoryBreadcrumbs()));
        }),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Молочные'));
      await tester.pump();

      final path = container.read(categoryPathProvider);
      expect(path, hasLength(1));
      expect(path.first.id, 1);
    });

    testWidgets('tap on the last (current) level does nothing', (tester) async {
      late ProviderContainer container;
      await tester.pumpWidget(ProviderScope(
        overrides: [
          categoryPathProvider.overrideWith((ref) => [_n(1, 'Молочные'), _n(11, 'Молоко')]),
        ],
        child: Builder(builder: (context) {
          container = ProviderScope.containerOf(context);
          return const MaterialApp(home: Scaffold(body: CategoryBreadcrumbs()));
        }),
      ));
      await tester.pumpAndSettle();

      // На последнем уровне ('Молоко') есть только текст без InkWell — тап
      // ничего не делает; убеждаемся, что состояние не изменилось.
      final beforeLength = container.read(categoryPathProvider).length;
      // Пытаемся тапнуть — структура текста просто Text, без InkWell.
      final lastTextWidget = tester.widget<Text>(find.text('Молоко'));
      expect(lastTextWidget.style?.fontWeight, FontWeight.bold);
      expect(
        find.ancestor(
          of: find.text('Молоко'),
          matching: find.byType(InkWell),
        ),
        findsNothing,
      );
      expect(container.read(categoryPathProvider).length, beforeLength);
    });
  });
}
