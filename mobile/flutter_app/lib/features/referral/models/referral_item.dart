class ReferralItem {
  final String fullName;
  final DateTime registeredAt;
  final bool hasPurchased;
  final String? rewardStatus; // pending | success | failed | null
  final double? bonusAmount;

  const ReferralItem({
    required this.fullName,
    required this.registeredAt,
    required this.hasPurchased,
    this.rewardStatus,
    this.bonusAmount,
  });

  factory ReferralItem.fromJson(Map<String, dynamic> json) {
    return ReferralItem(
      fullName: json['full_name'] as String? ?? '',
      registeredAt: DateTime.parse(json['registered_at'] as String),
      hasPurchased: json['has_purchased'] as bool? ?? false,
      rewardStatus: json['reward_status'] as String?,
      bonusAmount: (json['bonus_amount'] as num?)?.toDouble(),
    );
  }
}
