import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:lakshmi_market/features/loyalty/models/bonus_history_item.dart';
import 'package:lakshmi_market/features/loyalty/providers/bonus_history_provider.dart';
import 'package:lakshmi_market/features/loyalty/services/bonus_history_service.dart';

class MockBonusHistoryService extends Mock implements BonusHistoryService {}

BonusHistoryItem _makeItem({
  String guid = 'receipt-001',
  String date = '2025-06-15T10:00:00Z',
  double total = 1000.0,
  double earned = 50.0,
  double spent = 0.0,
}) =>
    BonusHistoryItem(
      receiptGuid: guid,
      date: DateTime.parse(date),
      purchaseTotal: total,
      bonusEarned: earned,
      bonusSpent: spent,
    );

void main() {
  late MockBonusHistoryService mockService;
  late BonusHistoryNotifier notifier;

  setUp(() {
    mockService = MockBonusHistoryService();
    notifier = BonusHistoryNotifier(mockService);
  });

  group('BonusHistoryNotifier', () {
    test('initial state is empty with no loading and no error', () {
      expect(notifier.state.items, isEmpty);
      expect(notifier.state.nextCursor, isNull);
      expect(notifier.state.isLoading, false);
      expect(notifier.state.error, isNull);
    });

    group('loadInitial', () {
      test('success — loads items and sets nextCursor', () async {
        when(() => mockService.getBonusHistory())
            .thenAnswer((_) async => BonusHistoryResponse(
                  results: [_makeItem(guid: 'r1'), _makeItem(guid: 'r2')],
                  nextCursor: 'cursor-page2',
                ));

        await notifier.loadInitial();

        expect(notifier.state.items.length, 2);
        expect(notifier.state.items[0].receiptGuid, 'r1');
        expect(notifier.state.items[1].receiptGuid, 'r2');
        expect(notifier.state.nextCursor, 'cursor-page2');
        expect(notifier.state.isLoading, false);
        expect(notifier.state.error, isNull);
      });

      test('success — no more pages sets nextCursor to null', () async {
        when(() => mockService.getBonusHistory())
            .thenAnswer((_) async => BonusHistoryResponse(
                  results: [_makeItem()],
                  nextCursor: null,
                ));

        await notifier.loadInitial();

        expect(notifier.state.items.length, 1);
        expect(notifier.state.nextCursor, isNull);
      });

      test('success — empty results', () async {
        when(() => mockService.getBonusHistory())
            .thenAnswer((_) async => BonusHistoryResponse(
                  results: [],
                  nextCursor: null,
                ));

        await notifier.loadInitial();

        expect(notifier.state.items, isEmpty);
        expect(notifier.state.nextCursor, isNull);
        expect(notifier.state.error, isNull);
      });

      test('error — sets error message', () async {
        when(() => mockService.getBonusHistory())
            .thenThrow(Exception('Сетевая ошибка'));

        await notifier.loadInitial();

        expect(notifier.state.items, isEmpty);
        expect(notifier.state.isLoading, false);
        expect(notifier.state.error, contains('Сетевая ошибка'));
      });
    });

    group('loadMore', () {
      test('success — appends items from next page', () async {
        // Setup initial state with cursor
        when(() => mockService.getBonusHistory())
            .thenAnswer((_) async => BonusHistoryResponse(
                  results: [_makeItem(guid: 'r1')],
                  nextCursor: 'cursor-page2',
                ));
        await notifier.loadInitial();

        // Load more
        when(() => mockService.getBonusHistory(cursor: 'cursor-page2'))
            .thenAnswer((_) async => BonusHistoryResponse(
                  results: [_makeItem(guid: 'r2'), _makeItem(guid: 'r3')],
                  nextCursor: 'cursor-page3',
                ));

        await notifier.loadMore();

        expect(notifier.state.items.length, 3);
        expect(notifier.state.items[0].receiptGuid, 'r1');
        expect(notifier.state.items[1].receiptGuid, 'r2');
        expect(notifier.state.items[2].receiptGuid, 'r3');
        expect(notifier.state.nextCursor, 'cursor-page3');
      });

      test('success — last page sets nextCursor to null', () async {
        when(() => mockService.getBonusHistory())
            .thenAnswer((_) async => BonusHistoryResponse(
                  results: [_makeItem(guid: 'r1')],
                  nextCursor: 'cursor-page2',
                ));
        await notifier.loadInitial();

        when(() => mockService.getBonusHistory(cursor: 'cursor-page2'))
            .thenAnswer((_) async => BonusHistoryResponse(
                  results: [_makeItem(guid: 'r2')],
                  nextCursor: null,
                ));

        await notifier.loadMore();

        expect(notifier.state.items.length, 2);
        expect(notifier.state.nextCursor, isNull);
      });

      test('guard — does nothing when nextCursor is null', () async {
        when(() => mockService.getBonusHistory())
            .thenAnswer((_) async => BonusHistoryResponse(
                  results: [_makeItem()],
                  nextCursor: null,
                ));
        await notifier.loadInitial();

        await notifier.loadMore();

        // Should not call service again
        verify(() => mockService.getBonusHistory()).called(1);
        verifyNever(() => mockService.getBonusHistory(cursor: any(named: 'cursor')));
      });

      test('error — preserves existing items and sets error', () async {
        when(() => mockService.getBonusHistory())
            .thenAnswer((_) async => BonusHistoryResponse(
                  results: [_makeItem(guid: 'r1')],
                  nextCursor: 'cursor-page2',
                ));
        await notifier.loadInitial();

        when(() => mockService.getBonusHistory(cursor: 'cursor-page2'))
            .thenThrow(Exception('Timeout'));

        await notifier.loadMore();

        expect(notifier.state.items.length, 1);
        expect(notifier.state.items[0].receiptGuid, 'r1');
        expect(notifier.state.error, contains('Timeout'));
        expect(notifier.state.isLoading, false);
      });
    });
  });

  group('BonusHistoryState', () {
    test('copyWith preserves values when no arguments given', () {
      final state = BonusHistoryState(
        items: [_makeItem()],
        nextCursor: 'c1',
        isLoading: true,
        error: 'err',
      );

      final copy = state.copyWith();

      expect(copy.items.length, 1);
      expect(copy.nextCursor, 'c1');
      expect(copy.isLoading, true);
      expect(copy.error, 'err');
    });

    test('copyWith clearCursor sets nextCursor to null', () {
      final state = BonusHistoryState(nextCursor: 'c1');
      final copy = state.copyWith(clearCursor: true);

      expect(copy.nextCursor, isNull);
    });

    test('copyWith clearError sets error to null', () {
      final state = BonusHistoryState(error: 'err');
      final copy = state.copyWith(clearError: true);

      expect(copy.error, isNull);
    });
  });
}
