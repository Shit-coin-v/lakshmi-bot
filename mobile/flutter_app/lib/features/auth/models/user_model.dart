class UserModel {
  final int id;
  final int? telegramId;
  final double bonusBalance;
  final String? qrCode;
  final String? fullName;
  final String? phone;
  final String? email;
  final String? avatarUrl;
  final bool emailVerified;
  final bool newsletterEnabled;
  final bool promoEnabled;
  final bool newsEnabled;
  final bool generalEnabled;

  UserModel({
    required this.id,
    this.telegramId,
    required this.bonusBalance,
    this.qrCode,
    this.fullName,
    this.phone,
    this.email,
    this.avatarUrl,
    this.emailVerified = false,
    this.newsletterEnabled = true,
    this.promoEnabled = true,
    this.newsEnabled = true,
    this.generalEnabled = true,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    final data = json.containsKey('customer') ? json['customer'] : json;

    return UserModel(
      id: data['id'] ?? 0,
      telegramId: data['telegram_id'],
      bonusBalance:
          double.tryParse(
            data['bonuses']?.toString() ??
                data['bonus_balance']?.toString() ??
                "0",
          ) ??
          0.0,
      qrCode: data['qr_code'],
      fullName: data['full_name'],
      phone: data['phone'],
      email: data['email'],
      avatarUrl: data['avatar'],
      emailVerified: data['email_verified'] ?? false,
      newsletterEnabled: data['newsletter_enabled'] ?? true,
      promoEnabled: data['promo_enabled'] ?? true,
      newsEnabled: data['news_enabled'] ?? true,
      generalEnabled: data['general_enabled'] ?? true,
    );
  }
}
