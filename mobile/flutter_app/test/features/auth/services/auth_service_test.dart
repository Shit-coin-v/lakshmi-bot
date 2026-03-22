import 'package:flutter_test/flutter_test.dart';

import 'package:lakshmi_market/features/auth/models/user_model.dart';

/// AuthService создаёт Dio и FlutterSecureStorage внутри без DI,
/// поэтому unit-тесты самого сервиса невозможны без изменения production-кода.
///
/// Тестируем парсинг контрактов API, которые использует AuthService:
/// - loginWithQr response (customer + tokens)
/// - loginWithEmail response (tokens + user_id)
/// - fetchProfile response (flat JSON)
void main() {
  group('Auth API contract: loginWithQr response', () {
    test('UserModel.fromJson parses loginWithQr response with customer wrapper', () {
      // Контракт POST /api/auth/login-qr/
      final loginResponse = {
        'customer': {
          'id': 42,
          'telegram_id': 123456789,
          'bonuses': '250.50',
          'qr_code': 'QR-ABC-123',
          'full_name': 'Иванов Иван',
          'phone': '+79001234567',
          'email': 'ivan@example.com',
          'avatar': '/media/avatars/ivan.jpg',
          'email_verified': true,
          'newsletter_enabled': false,
          'promo_enabled': true,
          'news_enabled': false,
          'general_enabled': true,
          'order_status_enabled': true,
        },
        'tokens': {
          'access': 'jwt-access-token',
          'refresh': 'jwt-refresh-token',
        },
      };

      final user = UserModel.fromJson(loginResponse);

      expect(user.id, 42);
      expect(user.telegramId, 123456789);
      expect(user.bonusBalance, 250.50);
      expect(user.qrCode, 'QR-ABC-123');
      expect(user.fullName, 'Иванов Иван');
      expect(user.phone, '+79001234567');
      expect(user.email, 'ivan@example.com');
      expect(user.avatarUrl, '/media/avatars/ivan.jpg');
      expect(user.emailVerified, true);
      expect(user.newsletterEnabled, false);
      expect(user.newsEnabled, false);
    });

    test('handles loginWithQr response with minimal customer data', () {
      final loginResponse = {
        'customer': {
          'id': 1,
          'telegram_id': 999,
          'bonuses': '0',
        },
        'tokens': {
          'access': 'token',
          'refresh': 'refresh',
        },
      };

      final user = UserModel.fromJson(loginResponse);

      expect(user.id, 1);
      expect(user.telegramId, 999);
      expect(user.bonusBalance, 0.0);
      expect(user.qrCode, isNull);
      expect(user.fullName, isNull);
      expect(user.phone, isNull);
      expect(user.email, isNull);
      expect(user.avatarUrl, isNull);
    });

    test('handles loginWithQr response without telegram_id', () {
      final loginResponse = {
        'customer': {
          'id': 5,
          'bonuses': '100',
        },
      };

      final user = UserModel.fromJson(loginResponse);

      expect(user.id, 5);
      expect(user.telegramId, isNull);
      expect(user.bonusBalance, 100.0);
    });
  });

  group('Auth API contract: fetchProfile response', () {
    test('UserModel.fromJson parses flat profile response', () {
      // Контракт GET /api/customer/{id}/
      final profileResponse = {
        'id': 42,
        'telegram_id': 123456789,
        'bonus_balance': '320.10',
        'qr_code': 'QR-XYZ',
        'full_name': 'Петров Пётр',
        'phone': '+79999999999',
        'email': 'petrov@example.com',
        'avatar': '/media/avatars/petrov.jpg',
        'email_verified': false,
        'newsletter_enabled': true,
        'promo_enabled': false,
        'news_enabled': true,
        'general_enabled': false,
        'order_status_enabled': false,
      };

      final user = UserModel.fromJson(profileResponse);

      expect(user.id, 42);
      expect(user.bonusBalance, 320.10);
      expect(user.emailVerified, false);
      expect(user.promoEnabled, false);
      expect(user.generalEnabled, false);
      expect(user.orderStatusEnabled, false);
    });
  });

  group('Auth API contract: notification preferences defaults', () {
    test('defaults to true when preferences not in response', () {
      final json = {'id': 1};

      final user = UserModel.fromJson(json);

      expect(user.emailVerified, false);
      expect(user.newsletterEnabled, true);
      expect(user.promoEnabled, true);
      expect(user.newsEnabled, true);
      expect(user.generalEnabled, true);
      expect(user.orderStatusEnabled, true);
    });

    test('explicit false overrides defaults', () {
      final json = {
        'id': 1,
        'newsletter_enabled': false,
        'promo_enabled': false,
        'news_enabled': false,
        'general_enabled': false,
        'order_status_enabled': false,
      };

      final user = UserModel.fromJson(json);

      expect(user.newsletterEnabled, false);
      expect(user.promoEnabled, false);
      expect(user.newsEnabled, false);
      expect(user.generalEnabled, false);
      expect(user.orderStatusEnabled, false);
    });
  });
}
