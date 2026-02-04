import 'package:flutter_test/flutter_test.dart';
import 'package:lakshmi_market/features/auth/models/user_model.dart';

void main() {
  group('UserModel', () {
    test('fromJson with customer wrapper parses inner data', () {
      final json = {
        'customer': {
          'id': 42,
          'telegram_id': 123456,
          'bonuses': '150.50',
          'qr_code': 'QR123',
          'full_name': 'John Doe',
          'phone': '+71234567890',
          'email': 'john@example.com',
          'avatar': 'https://example.com/avatar.png',
        }
      };

      final user = UserModel.fromJson(json);

      expect(user.id, 42);
      expect(user.telegramId, 123456);
      expect(user.bonusBalance, 150.50);
      expect(user.qrCode, 'QR123');
      expect(user.fullName, 'John Doe');
      expect(user.phone, '+71234567890');
      expect(user.email, 'john@example.com');
      expect(user.avatarUrl, 'https://example.com/avatar.png');
    });

    test('fromJson without wrapper parses directly', () {
      final json = {
        'id': 7,
        'telegram_id': 999,
        'bonuses': '10.0',
        'full_name': 'Jane',
      };

      final user = UserModel.fromJson(json);

      expect(user.id, 7);
      expect(user.telegramId, 999);
      expect(user.bonusBalance, 10.0);
      expect(user.fullName, 'Jane');
    });

    test('bonuses key parsed as double', () {
      final json = {
        'id': 1,
        'telegram_id': 1,
        'bonuses': '255.99',
      };

      final user = UserModel.fromJson(json);

      expect(user.bonusBalance, 255.99);
    });

    test('bonus_balance key parsed as double when bonuses is absent', () {
      final json = {
        'id': 1,
        'telegram_id': 1,
        'bonus_balance': '320.10',
      };

      final user = UserModel.fromJson(json);

      expect(user.bonusBalance, 320.10);
    });

    test('missing bonuses defaults to 0.0', () {
      final json = {
        'id': 1,
        'telegram_id': 1,
      };

      final user = UserModel.fromJson(json);

      expect(user.bonusBalance, 0.0);
    });

    test('nullable fields are null when absent', () {
      final json = {
        'id': 1,
        'telegram_id': 1,
      };

      final user = UserModel.fromJson(json);

      expect(user.qrCode, isNull);
      expect(user.fullName, isNull);
      expect(user.phone, isNull);
      expect(user.email, isNull);
    });

    test('avatar key maps to avatarUrl', () {
      final json = {
        'id': 1,
        'telegram_id': 1,
        'avatar': 'https://cdn.example.com/photo.jpg',
      };

      final user = UserModel.fromJson(json);

      expect(user.avatarUrl, 'https://cdn.example.com/photo.jpg');
    });
  });
}
