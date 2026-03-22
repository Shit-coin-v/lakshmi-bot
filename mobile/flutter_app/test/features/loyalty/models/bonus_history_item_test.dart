import 'package:flutter_test/flutter_test.dart';
import 'package:lakshmi_market/features/loyalty/models/bonus_history_item.dart';

void main() {
  group('BonusHistoryItem', () {
    test('fromJson parses all fields correctly', () {
      final json = {
        'receipt_guid': 'RCP-001',
        'date': '2026-03-10T14:30:00Z',
        'purchase_total': '1500.50',
        'bonus_earned': '75.02',
        'bonus_spent': '100.00',
      };

      final item = BonusHistoryItem.fromJson(json);

      expect(item.receiptGuid, 'RCP-001');
      expect(item.date.year, 2026);
      expect(item.date.month, 3);
      expect(item.date.day, 10);
      expect(item.purchaseTotal, 1500.50);
      expect(item.bonusEarned, 75.02);
      expect(item.bonusSpent, 100.00);
    });

    test('fromJson parses numeric values via double.tryParse', () {
      final json = {
        'receipt_guid': 'RCP-002',
        'date': '2026-01-01T00:00:00Z',
        'purchase_total': 999,
        'bonus_earned': 50,
        'bonus_spent': 0,
      };

      final item = BonusHistoryItem.fromJson(json);

      expect(item.purchaseTotal, 999.0);
      expect(item.bonusEarned, 50.0);
      expect(item.bonusSpent, 0.0);
    });

    test('fromJson defaults to 0.0 for null values', () {
      final json = {
        'receipt_guid': 'RCP-003',
        'date': '2026-01-01T00:00:00Z',
        'purchase_total': null,
        'bonus_earned': null,
        'bonus_spent': null,
      };

      final item = BonusHistoryItem.fromJson(json);

      expect(item.purchaseTotal, 0.0);
      expect(item.bonusEarned, 0.0);
      expect(item.bonusSpent, 0.0);
    });
  });

  group('BonusHistoryResponse', () {
    test('fromJson parses results and nextCursor', () {
      final json = {
        'results': [
          {
            'receipt_guid': 'RCP-A',
            'date': '2026-03-01T10:00:00Z',
            'purchase_total': '200.00',
            'bonus_earned': '10.00',
            'bonus_spent': '0.00',
          },
          {
            'receipt_guid': 'RCP-B',
            'date': '2026-03-02T11:00:00Z',
            'purchase_total': '300.00',
            'bonus_earned': '15.00',
            'bonus_spent': '5.00',
          },
        ],
        'next_cursor': 'cursor-abc-123',
      };

      final response = BonusHistoryResponse.fromJson(json);

      expect(response.results.length, 2);
      expect(response.results[0].receiptGuid, 'RCP-A');
      expect(response.results[1].receiptGuid, 'RCP-B');
      expect(response.nextCursor, 'cursor-abc-123');
    });

    test('fromJson with empty results', () {
      final json = {
        'results': [],
        'next_cursor': null,
      };

      final response = BonusHistoryResponse.fromJson(json);

      expect(response.results, isEmpty);
      expect(response.nextCursor, isNull);
    });

    test('fromJson with nextCursor null', () {
      final json = {
        'results': [
          {
            'receipt_guid': 'RCP-X',
            'date': '2026-03-15T09:00:00Z',
            'purchase_total': '100.00',
            'bonus_earned': '5.00',
            'bonus_spent': '0.00',
          },
        ],
        'next_cursor': null,
      };

      final response = BonusHistoryResponse.fromJson(json);

      expect(response.results.length, 1);
      expect(response.nextCursor, isNull);
    });
  });
}
