import 'package:flutter_test/flutter_test.dart';

import 'package:lakshmi_market/features/loyalty/models/bonus_history_item.dart';

/// BonusHistoryService creates Dio internally via ApiClient().dio,
/// so we cannot inject a mock without changing production code.
/// Instead, we test the data model parsing (BonusHistoryResponse.fromJson)
/// which is what the service delegates to.
void main() {
  group('BonusHistoryResponse.fromJson', () {
    test('parses results with nextCursor', () {
      final json = {
        'results': [
          {
            'receipt_guid': 'abc-123',
            'date': '2025-06-15T10:00:00Z',
            'purchase_total': '1500.50',
            'bonus_earned': '75.03',
            'bonus_spent': '0.00',
          },
          {
            'receipt_guid': 'def-456',
            'date': '2025-06-14T08:30:00Z',
            'purchase_total': '320',
            'bonus_earned': '16',
            'bonus_spent': '50',
          },
        ],
        'next_cursor': 'cursor-abc',
      };

      final response = BonusHistoryResponse.fromJson(json);

      expect(response.results.length, 2);
      expect(response.nextCursor, 'cursor-abc');
      expect(response.results[0].receiptGuid, 'abc-123');
      expect(response.results[0].purchaseTotal, 1500.50);
      expect(response.results[0].bonusEarned, 75.03);
      expect(response.results[0].bonusSpent, 0.0);
      expect(response.results[1].receiptGuid, 'def-456');
      expect(response.results[1].purchaseTotal, 320.0);
      expect(response.results[1].bonusSpent, 50.0);
    });

    test('parses empty results with null nextCursor', () {
      final json = {
        'results': [],
        'next_cursor': null,
      };

      final response = BonusHistoryResponse.fromJson(json);

      expect(response.results, isEmpty);
      expect(response.nextCursor, isNull);
    });

    test('parses results without next_cursor key', () {
      final json = {
        'results': [
          {
            'receipt_guid': 'x',
            'date': '2025-01-01T00:00:00Z',
            'purchase_total': '100',
            'bonus_earned': '5',
            'bonus_spent': '0',
          },
        ],
      };

      final response = BonusHistoryResponse.fromJson(json);

      expect(response.results.length, 1);
      expect(response.nextCursor, isNull);
    });
  });

  group('BonusHistoryItem.fromJson', () {
    test('handles numeric strings for amounts', () {
      final item = BonusHistoryItem.fromJson({
        'receipt_guid': 'g1',
        'date': '2025-03-20T12:00:00Z',
        'purchase_total': '999.99',
        'bonus_earned': '49.99',
        'bonus_spent': '10.00',
      });

      expect(item.receiptGuid, 'g1');
      expect(item.purchaseTotal, 999.99);
      expect(item.bonusEarned, 49.99);
      expect(item.bonusSpent, 10.0);
    });

    test('handles null amounts gracefully', () {
      final item = BonusHistoryItem.fromJson({
        'receipt_guid': 'g2',
        'date': '2025-03-20T12:00:00Z',
        'purchase_total': null,
        'bonus_earned': null,
        'bonus_spent': null,
      });

      expect(item.purchaseTotal, 0.0);
      expect(item.bonusEarned, 0.0);
      expect(item.bonusSpent, 0.0);
    });

    test('handles integer amounts', () {
      final item = BonusHistoryItem.fromJson({
        'receipt_guid': 'g3',
        'date': '2025-03-20T12:00:00Z',
        'purchase_total': 500,
        'bonus_earned': 25,
        'bonus_spent': 0,
      });

      expect(item.purchaseTotal, 500.0);
      expect(item.bonusEarned, 25.0);
      expect(item.bonusSpent, 0.0);
    });
  });
}
