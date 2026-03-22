class BonusHistoryItem {
  final String receiptGuid;
  final DateTime date;
  final double purchaseTotal;
  final double bonusEarned;
  final double bonusSpent;

  BonusHistoryItem({
    required this.receiptGuid,
    required this.date,
    required this.purchaseTotal,
    required this.bonusEarned,
    required this.bonusSpent,
  });

  factory BonusHistoryItem.fromJson(Map<String, dynamic> json) {
    return BonusHistoryItem(
      receiptGuid: json['receipt_guid'] as String,
      date: DateTime.parse(json['date'] as String),
      purchaseTotal: double.tryParse(json['purchase_total']?.toString() ?? '') ?? 0.0,
      bonusEarned: double.tryParse(json['bonus_earned']?.toString() ?? '') ?? 0.0,
      bonusSpent: double.tryParse(json['bonus_spent']?.toString() ?? '') ?? 0.0,
    );
  }
}

class BonusHistoryResponse {
  final List<BonusHistoryItem> results;
  final String? nextCursor;

  BonusHistoryResponse({
    required this.results,
    this.nextCursor,
  });

  factory BonusHistoryResponse.fromJson(Map<String, dynamic> json) {
    return BonusHistoryResponse(
      results: (json['results'] as List<dynamic>)
          .map((e) => BonusHistoryItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      nextCursor: json['next_cursor'] as String?,
    );
  }
}
