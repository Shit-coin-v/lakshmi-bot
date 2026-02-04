import 'package:flutter_test/flutter_test.dart';
import 'package:lakshmi_market/features/notifications/models/notification_model.dart';

void main() {
  group('NotificationModel', () {
    test('fromJson with snake_case keys', () {
      final json = {
        'id': 1,
        'title': 'Заказ готов',
        'body': 'Ваш заказ #55 готов к выдаче',
        'created_at': '2025-08-10T12:00:00Z',
        'is_read': true,
        'type': 'personal',
      };

      final notification = NotificationModel.fromJson(json);

      expect(notification.id, '1');
      expect(notification.title, 'Заказ готов');
      expect(notification.body, 'Ваш заказ #55 готов к выдаче');
      expect(notification.isRead, isTrue);
      expect(notification.type, 'personal');
      expect(notification.date.year, 2025);
      expect(notification.date.month, 8);
      expect(notification.date.day, 10);
    });

    test('fromJson with camelCase keys', () {
      final json = {
        'id': 2,
        'title': 'Промо акция',
        'body': 'Скидка 20% на все товары',
        'createdAt': '2025-09-01T09:30:00Z',
        'isRead': false,
        'type': 'broadcast',
      };

      final notification = NotificationModel.fromJson(json);

      expect(notification.id, '2');
      expect(notification.title, 'Промо акция');
      expect(notification.body, 'Скидка 20% на все товары');
      expect(notification.isRead, isFalse);
      expect(notification.type, 'broadcast');
      expect(notification.date.year, 2025);
      expect(notification.date.month, 9);
    });

    test('title falls back to subject, then to default', () {
      // Falls back to subject
      final json1 = {
        'id': 3,
        'subject': 'Тема письма',
        'body': 'text',
        'created_at': '2025-01-01T00:00:00Z',
      };
      final n1 = NotificationModel.fromJson(json1);
      expect(n1.title, 'Тема письма');

      // Falls back to default when neither title nor subject present
      final json2 = {
        'id': 4,
        'body': 'text',
        'created_at': '2025-01-01T00:00:00Z',
      };
      final n2 = NotificationModel.fromJson(json2);
      expect(n2.title, 'Уведомление');
    });

    test('default isRead is false', () {
      final json = {
        'id': 5,
        'title': 'Test',
        'body': 'Body',
        'created_at': '2025-01-01T00:00:00Z',
      };

      final notification = NotificationModel.fromJson(json);

      expect(notification.isRead, isFalse);
    });

    test('invalid date defaults to approximately DateTime.now()', () {
      final before = DateTime.now();
      final json = {
        'id': 6,
        'title': 'Test',
        'body': 'Body',
        'created_at': 'invalid-date',
      };

      final notification = NotificationModel.fromJson(json);
      final after = DateTime.now();

      expect(notification.date, isNotNull);
      expect(
        notification.date
            .isAfter(before.subtract(const Duration(seconds: 1))),
        isTrue,
      );
      expect(
        notification.date.isBefore(after.add(const Duration(seconds: 1))),
        isTrue,
      );
    });

    test('copyWith toggles isRead', () {
      final notification = NotificationModel(
        id: '10',
        title: 'Hello',
        body: 'World',
        date: DateTime(2025, 1, 1),
        isRead: false,
        type: 'personal',
      );

      final toggled = notification.copyWith(isRead: true);

      expect(toggled.isRead, isTrue);
      expect(toggled.id, '10');
      expect(toggled.title, 'Hello');
      expect(toggled.body, 'World');
      expect(toggled.type, 'personal');

      // Toggle back
      final toggledBack = toggled.copyWith(isRead: false);
      expect(toggledBack.isRead, isFalse);
    });
  });
}
