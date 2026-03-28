class ReferralStats {
  final int registeredCount;
  final int purchasedCount;
  final double bonusEarned;

  const ReferralStats({
    required this.registeredCount,
    required this.purchasedCount,
    required this.bonusEarned,
  });

  factory ReferralStats.fromJson(Map<String, dynamic> json) {
    return ReferralStats(
      registeredCount: json['registered_count'] as int? ?? 0,
      purchasedCount: json['purchased_count'] as int? ?? 0,
      bonusEarned: (json['bonus_earned'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class ReferralInfo {
  final String referralCode;
  final String referralLink;
  final ReferralStats stats;

  const ReferralInfo({
    required this.referralCode,
    required this.referralLink,
    required this.stats,
  });

  factory ReferralInfo.fromJson(Map<String, dynamic> json) {
    return ReferralInfo(
      referralCode: json['referral_code'] as String? ?? '',
      referralLink: json['referral_link'] as String? ?? '',
      stats: ReferralStats.fromJson(json['stats'] as Map<String, dynamic>? ?? {}),
    );
  }
}
