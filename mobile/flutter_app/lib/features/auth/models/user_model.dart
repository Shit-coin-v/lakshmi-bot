class UserModel {
  final int id;
  final int telegramId;
  final double bonusBalance;
  final String? qrCode;
  final String? fullName;
  final String? phone;
  final String? email;
  final String? avatarUrl;
  final bool newsletterEnabled;

  UserModel({
    required this.id,
    required this.telegramId,
    required this.bonusBalance,
    this.qrCode,
    this.fullName,
    this.phone,
    this.email,
    this.avatarUrl,
    this.newsletterEnabled = true,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    final data = json.containsKey('customer') ? json['customer'] : json;

    return UserModel(
      id: data['id'] ?? 0,
      telegramId: data['telegram_id'] ?? 0,
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
      newsletterEnabled: data['newsletter_enabled'] ?? true,
    );
  }
}
