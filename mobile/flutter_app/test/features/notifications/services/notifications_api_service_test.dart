import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:lakshmi_market/features/notifications/services/notifications_api_service.dart';
import 'package:lakshmi_market/features/notifications/models/notification_model.dart';

import '../../../helpers/mocks.dart';

void main() {
  late MockDio mockDio;
  late NotificationsApiService service;

  setUp(() {
    mockDio = MockDio();
    service = NotificationsApiService(dio: mockDio);
  });

  group('NotificationsApiService', () {
    test('fetchNotifications parses list of notifications', () async {
      when(() => mockDio.get(
            '/api/notifications/',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => Response(
            data: [
              {
                'id': 1,
                'title': 'Акция',
                'body': 'Скидки на молоко!',
                'created_at': '2025-06-15T10:30:00Z',
                'is_read': false,
                'type': 'broadcast',
              },
              {
                'id': 2,
                'title': 'Заказ готов',
                'body': 'Ваш заказ №5 готов к выдаче',
                'created_at': '2025-06-14T08:00:00Z',
                'is_read': true,
                'type': 'personal',
              },
            ],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/notifications/'),
          ));

      final notifications = await service.fetchNotifications(userId: 42);

      expect(notifications, isA<List<NotificationModel>>());
      expect(notifications.length, 2);
      expect(notifications[0].id, '1');
      expect(notifications[0].title, 'Акция');
      expect(notifications[0].body, 'Скидки на молоко!');
      expect(notifications[0].isRead, false);
      expect(notifications[0].type, 'broadcast');
      expect(notifications[1].id, '2');
      expect(notifications[1].isRead, true);
    });

    test('fetchNotifications returns empty list when data is not List',
        () async {
      when(() => mockDio.get(
            '/api/notifications/',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => Response(
            data: 'unexpected string response',
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/notifications/'),
          ));

      final notifications = await service.fetchNotifications(userId: 42);

      expect(notifications, isEmpty);
    });

    test('fetchNotifications passes userId as query param', () async {
      when(() => mockDio.get(
            '/api/notifications/',
            queryParameters: {'user_id': 42},
          )).thenAnswer((_) async => Response(
            data: [],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/notifications/'),
          ));

      await service.fetchNotifications(userId: 42);

      verify(() => mockDio.get(
            '/api/notifications/',
            queryParameters: {'user_id': 42},
          )).called(1);
    });

    test('markAsRead sends POST with correct payload', () async {
      when(() => mockDio.post(
            '/api/notifications/7/read/',
            data: {'user_id': 42, 'source': 'inapp'},
          )).thenAnswer((_) async => Response(
            data: {},
            statusCode: 200,
            requestOptions:
                RequestOptions(path: '/api/notifications/7/read/'),
          ));

      await service.markAsRead(notificationId: 7, userId: 42);

      verify(() => mockDio.post(
            '/api/notifications/7/read/',
            data: {'user_id': 42, 'source': 'inapp'},
          )).called(1);
    });
  });
}
