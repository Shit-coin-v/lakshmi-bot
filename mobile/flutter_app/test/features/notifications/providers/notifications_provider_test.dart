import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:lakshmi_market/features/notifications/models/notification_model.dart';
import 'package:lakshmi_market/features/notifications/providers/notifications_provider.dart';
import 'package:lakshmi_market/features/notifications/services/notifications_api_service.dart';

class MockNotificationsApiService extends Mock
    implements NotificationsApiService {}

NotificationModel _makeNotification({
  String id = '1',
  String title = 'Test',
  String body = 'Body',
  bool isRead = false,
}) =>
    NotificationModel(
      id: id,
      title: title,
      body: body,
      date: DateTime(2025, 1, 1),
      isRead: isRead,
    );

void main() {
  late MockNotificationsApiService mockApi;

  setUp(() {
    mockApi = MockNotificationsApiService();
  });

  group('NotificationsNotifier', () {
    test('loadNotifications succeeds', () async {
      when(() => mockApi.fetchNotifications()).thenAnswer(
        (_) async => [
          _makeNotification(id: '1', title: 'Hello'),
          _makeNotification(id: '2', title: 'World'),
        ],
      );

      final container = ProviderContainer(overrides: [
        notificationsApiServiceProvider.overrideWithValue(mockApi),
      ]);
      addTearDown(container.dispose);

      // Access the provider to trigger construction + loadNotifications
      container.read(notificationsProvider.notifier);

      // Let async loadNotifications complete
      await Future.delayed(Duration.zero);

      final state = container.read(notificationsProvider);
      expect(state, isA<AsyncData<List<NotificationModel>>>());

      final data = state.value!;
      expect(data, hasLength(2));
      expect(data[0].title, 'Hello');
      expect(data[1].title, 'World');

      verify(() => mockApi.fetchNotifications()).called(1);
    });

    test('loadNotifications errors when API throws', () async {
      when(() => mockApi.fetchNotifications())
          .thenThrow(Exception('Network error'));

      final container = ProviderContainer(overrides: [
        notificationsApiServiceProvider.overrideWithValue(mockApi),
      ]);
      addTearDown(container.dispose);

      container.read(notificationsProvider.notifier);

      // Let async loadNotifications complete
      await Future.delayed(Duration.zero);

      final state = container.read(notificationsProvider);
      expect(state, isA<AsyncError<List<NotificationModel>>>());
    });

    test('markAsRead updates local state', () async {
      when(() => mockApi.fetchNotifications()).thenAnswer(
        (_) async => [
          _makeNotification(id: '10', title: 'Unread', isRead: false),
        ],
      );
      when(() => mockApi.markAsRead(
            notificationId: 10,
          )).thenAnswer((_) async {});

      final container = ProviderContainer(overrides: [
        notificationsApiServiceProvider.overrideWithValue(mockApi),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(notificationsProvider.notifier);
      await Future.delayed(Duration.zero);

      // Verify loaded as unread
      expect(notifier.state.value!.first.isRead, isFalse);

      await notifier.markAsRead('10');

      expect(notifier.state.value!.first.isRead, isTrue);

      verify(() => mockApi.markAsRead(notificationId: 10))
          .called(1);
    });

    test('clearAll empties the list', () async {
      when(() => mockApi.fetchNotifications()).thenAnswer(
        (_) async => [
          _makeNotification(id: '1'),
          _makeNotification(id: '2'),
        ],
      );

      final container = ProviderContainer(overrides: [
        notificationsApiServiceProvider.overrideWithValue(mockApi),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(notificationsProvider.notifier);
      await Future.delayed(Duration.zero);

      // Verify we have items first
      expect(notifier.state.value!, hasLength(2));

      notifier.clearAll();

      expect(notifier.state, isA<AsyncData<List<NotificationModel>>>());
      expect(notifier.state.value!, isEmpty);
    });
  });
}
