import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';

import 'package:lakshmi_market/features/home/services/profile_service.dart';
import 'package:lakshmi_market/features/auth/services/auth_service.dart';
import 'package:lakshmi_market/features/auth/models/user_model.dart';

import '../../../helpers/mocks.dart';

void main() {
  late MockDio mockDio;
  late MockAuthService mockAuth;

  setUp(() {
    mockDio = MockDio();
    mockAuth = MockAuthService();
  });

  ProviderContainer createContainer() {
    final container = ProviderContainer(overrides: [
      authServiceProvider.overrideWithValue(mockAuth),
      profileServiceProvider
          .overrideWith((ref) => ProfileService(ref, dio: mockDio)),
    ]);
    return container;
  }

  group('ProfileService', () {
    test('getProfile calls GET with correct userId and returns UserModel',
        () async {
      when(() => mockAuth.getSavedUserId()).thenAnswer((_) async => 42);
      when(() => mockDio.get('/api/customer/42/')).thenAnswer((_) async =>
          Response(
            data: {
              'id': 42,
              'telegram_id': 123456,
              'bonuses': '150.50',
              'full_name': 'Иван Иванов',
              'phone': '+79991234567',
              'email': 'ivan@test.com',
              'qr_code': 'QR123',
              'avatar': null,
            },
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/customer/42/'),
          ));

      final container = createContainer();
      addTearDown(container.dispose);

      final service = container.read(profileServiceProvider);
      final user = await service.getProfile();

      expect(user, isA<UserModel>());
      expect(user.id, 42);
      expect(user.telegramId, 123456);
      expect(user.bonusBalance, 150.50);
      expect(user.fullName, 'Иван Иванов');
      expect(user.phone, '+79991234567');
      expect(user.email, 'ivan@test.com');

      verify(() => mockDio.get('/api/customer/42/')).called(1);
    });

    test('getProfile throws when userId is null', () async {
      when(() => mockAuth.getSavedUserId()).thenAnswer((_) async => null);

      final container = createContainer();
      addTearDown(container.dispose);

      final service = container.read(profileServiceProvider);

      expect(
        () => service.getProfile(),
        throwsA(isA<Exception>().having(
          (e) => e.toString(),
          'message',
          contains('Не найден ID пользователя'),
        )),
      );
    });

    test('updateProfile sends PATCH with all provided fields', () async {
      when(() => mockAuth.getSavedUserId()).thenAnswer((_) async => 42);
      when(() => mockDio.patch(
            '/api/customer/42/',
            data: {
              'full_name': 'Петр Петров',
              'phone': '+79998887766',
              'email': 'petr@test.com',
            },
          )).thenAnswer((_) async => Response(
            data: {},
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/customer/42/'),
          ));

      final container = createContainer();
      addTearDown(container.dispose);

      final service = container.read(profileServiceProvider);
      await service.updateProfile(
        fullName: 'Петр Петров',
        phone: '+79998887766',
        email: 'petr@test.com',
      );

      verify(() => mockDio.patch(
            '/api/customer/42/',
            data: {
              'full_name': 'Петр Петров',
              'phone': '+79998887766',
              'email': 'petr@test.com',
            },
          )).called(1);
    });

    test('updateProfile with only some fields sends only those', () async {
      when(() => mockAuth.getSavedUserId()).thenAnswer((_) async => 42);
      when(() => mockDio.patch(
            '/api/customer/42/',
            data: {'phone': '+79998887766'},
          )).thenAnswer((_) async => Response(
            data: {},
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/customer/42/'),
          ));

      final container = createContainer();
      addTearDown(container.dispose);

      final service = container.read(profileServiceProvider);
      await service.updateProfile(phone: '+79998887766');

      verify(() => mockDio.patch(
            '/api/customer/42/',
            data: {'phone': '+79998887766'},
          )).called(1);
    });
  });
}
