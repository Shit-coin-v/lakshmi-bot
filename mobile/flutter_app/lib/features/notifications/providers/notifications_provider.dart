import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_client.dart';
import '../models/notification_model.dart';
import '../services/notifications_api_service.dart';

final notificationsApiServiceProvider = Provider<NotificationsApiService>(
  (ref) => NotificationsApiService(),
);

class NotificationsNotifier
    extends StateNotifier<AsyncValue<List<NotificationModel>>> {
  NotificationsNotifier(this._ref) : super(const AsyncValue.data([])) {
    _initLoad();
  }

  final Ref _ref;

  void _initLoad() {
    if (ApiClient().hasAccessToken) {
      loadNotifications();
    }
  }

  Future<void> loadNotifications() async {
    if (!ApiClient().hasAccessToken) return;
    state = const AsyncValue.loading();
    try {
      final api = _ref.read(notificationsApiServiceProvider);
      final items = await api.fetchNotifications();

      state = AsyncValue.data(items);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> markAsRead(String id) async {
    final current = state;
    if (current is! AsyncData<List<NotificationModel>>) return;

    final notifId = int.tryParse(id);
    if (notifId == null) return;

    try {
      final api = _ref.read(notificationsApiServiceProvider);
      await api.markAsRead(notificationId: notifId);

      final updated = [
        for (final n in current.value)
          if (n.id == id) n.copyWith(isRead: true) else n,
      ];
      state = AsyncValue.data(updated);
    } catch (_) {
      state = current;
    }
  }

  Future<void> markAllAsRead() async {
    final current = state;
    if (current is! AsyncData<List<NotificationModel>>) return;

    try {
      final api = _ref.read(notificationsApiServiceProvider);
      await api.markAllAsRead();

      final updated = [
        for (final n in current.value) n.copyWith(isRead: true),
      ];
      state = AsyncValue.data(updated);
    } catch (_) {
      state = current;
    }
  }

  void clearAll() {
    state = const AsyncValue.data([]);
  }
}

final notificationsProvider =
    StateNotifierProvider<
      NotificationsNotifier,
      AsyncValue<List<NotificationModel>>
    >((ref) => NotificationsNotifier(ref));
