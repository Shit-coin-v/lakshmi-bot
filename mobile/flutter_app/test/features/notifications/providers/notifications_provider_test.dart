import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:lakshmi_market/features/auth/services/auth_service.dart';
import 'package:lakshmi_market/features/notifications/models/notification_model.dart';
import 'package:lakshmi_market/features/notifications/providers/notifications_provider.dart';
import 'package:lakshmi_market/features/notifications/services/notifications_api_service.dart';

class MockAuthService extends Mock implements AuthService {}

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
  late MockAuthService mockAuth;
  late MockNotificationsApiService mockApi;

  setUp(() {
    mockAuth = MockAuthService();
    mockApi = MockNotificationsApiService();
  });

  group('NotificationsNotifier', () {
    test('loadNotifications succeeds with valid userId', () async {
      when(() => mockAuth.getSavedUserId()).thenAnswer((_) async => 1);
      when(() => mockApi.fetchNotifications(userId: 1)).thenAnswer(
        (_) async => [
          _makeNotification(id: '1', title: 'Hello'),
          _makeNotification(id: '2', title: 'World'),
        ],
      );

      final container = ProviderContainer(overrides: [
        authServiceProvider.overrideWithValue(mockAuth),
        notificationsApiServiceProvider.overrideWithValue(mockApi),
      ]);
      addTearDown(container.dispose);

      // Access the provider to trigger construction + loadNotifications
      final notifier = container.read(notificationsProvider.notifier);

      // Let async loadNotifications complete
      await Future.delayed(Duration.zero);

      final state = notifier.debugState;
      expect(state, isA<AsyncData<List<NotificationModel>>>());

      final data = state.value!;
      expect(data, hasLength(2));
      expect(data[0].title, 'Hello');
      expect(data[1].title, 'World');

      verify(() => mockAuth.getSavedUserId()).called(1);
      verify(() => mockApi.fetchNotifications(userId: 1)).called(1);
    });

    test('loadNotifications errors when userId is null', () async {
      when(() => mockAuth.getSavedUserId()).thenAnswer((_) async => null);

      final container = ProviderContainer(overrides: [
        authServiceProvider.overrideWithValue(mockAuth),
        notificationsApiServiceProvider.overrideWithValue(mockApi),
      ]);
      addTearDown(container.dispose);

      container.read(notificationsProvider.notifier);

      // Let async loadNotifications complete
      await Future.delayed(Duration.zero);

      final state = container.read(notificationsProvider);
      expect(state, isA<AsyncError<List<NotificationModel>>>());

      verifyNever(
          () => mockApi.fetchNotifications(userId: any(named: 'userId')));
    });

    test('markAsRead updates local state', () async {
      when(() => mockAuth.getSavedUserId()).thenAnswer((_) async => 1);
      when(() => mockApi.fetchNotifications(userId: 1)).thenAnswer(
        (_) async => [
          _makeNotification(id: '10', title: 'Unread', isRead: false),
        ],
      );
      when(() => mockApi.markAsRead(
            notificationId: 10,
            userId: 1,
          )).thenAnswer((_) async {});

      final container = ProviderContainer(overrides: [
        authServiceProvider.overrideWithValue(mockAuth),
        notificationsApiServiceProvider.overrideWithValue(mockApi),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(notificationsProvider.notifier);
      await Future.delayed(Duration.zero);

      // Verify loaded as unread
      expect(notifier.debugState.value!.first.isRead, isFalse);

      await notifier.markAsRead('10');

      expect(notifier.debugState.value!.first.isRead, isTrue);

      verify(() => mockApi.markAsRead(notificationId: 10, userId: 1))
          .called(1);
    });

    test('clearAll empties the list', () async {
      when(() => mockAuth.getSavedUserId()).thenAnswer((_) async => 1);
      when(() => mockApi.fetchNotifications(userId: 1)).thenAnswer(
        (_) async => [
          _makeNotification(id: '1'),
          _makeNotification(id: '2'),
        ],
      );

      final container = ProviderContainer(overrides: [
        authServiceProvider.overrideWithValue(mockAuth),
        notificationsApiServiceProvider.overrideWithValue(mockApi),
      ]);
      addTearDown(container.dispose);

      final notifier = container.read(notificationsProvider.notifier);
      await Future.delayed(Duration.zero);

      // Verify we have items first
      expect(notifier.debugState.value!, hasLength(2));

      notifier.clearAll();

      expect(notifier.debugState, isA<AsyncData<List<NotificationModel>>>());
      expect(notifier.debugState.value!, isEmpty);
    });
  });
}
