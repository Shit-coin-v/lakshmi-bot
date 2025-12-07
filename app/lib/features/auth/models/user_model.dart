class UserModel {
  final int telegramId;
  final double bonusBalance;
  final String? qrCode;

  UserModel({
    required this.telegramId,
    required this.bonusBalance,
    this.qrCode,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    // В ответе сервера данные лежат внутри ключа "customer"
    // Но иногда мы можем передать сразу внутренность "customer".
    // Сделаем универсально:
    final data = json.containsKey('customer') ? json['customer'] : json;

    return UserModel(
      telegramId: data['telegram_id'] ?? 0,
      // Приводим к double аккуратно, так как может прийти int или string
      bonusBalance: double.tryParse(data['bonus_balance'].toString()) ?? 0.0,
      qrCode: data['qr_code'],
    );
  }
}
