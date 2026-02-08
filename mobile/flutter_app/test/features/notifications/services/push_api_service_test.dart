import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:lakshmi_market/features/notifications/services/push_api_service.dart';

import '../../../helpers/mocks.dart';

void main() {
  late MockDio mockDio;
  late PushApiService service;

  setUp(() {
    mockDio = MockDio();
    service = PushApiService(dio: mockDio);
  });

  group('PushApiService', () {
    test('registerToken sends correct payload', () async {
      when(() => mockDio.post(
            '/api/fcm/token/',
            data: {
              'fcm_token': 'abc123fcmtoken',
              'platform': 'ios',
            },
          )).thenAnswer((_) async => Response(
            data: {},
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/fcm/token/'),
          ));

      await service.registerToken(
        fcmToken: 'abc123fcmtoken',
        platform: 'ios',
      );

      verify(() => mockDio.post(
            '/api/fcm/token/',
            data: {
              'fcm_token': 'abc123fcmtoken',
              'platform': 'ios',
            },
          )).called(1);
    });

    test('registerToken defaults platform to android', () async {
      when(() => mockDio.post(
            '/api/fcm/token/',
            data: {
              'fcm_token': 'xyz789token',
              'platform': 'android',
            },
          )).thenAnswer((_) async => Response(
            data: {},
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/fcm/token/'),
          ));

      // Call without specifying platform to use default 'android'
      await service.registerToken(
        fcmToken: 'xyz789token',
      );

      verify(() => mockDio.post(
            '/api/fcm/token/',
            data: {
              'fcm_token': 'xyz789token',
              'platform': 'android',
            },
          )).called(1);
    });
  });
}
