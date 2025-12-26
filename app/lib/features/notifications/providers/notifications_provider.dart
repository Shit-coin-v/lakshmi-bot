import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/services/auth_service.dart';
import '../models/notification_model.dart';
import '../services/notifications_api_service.dart';

final notificationsApiServiceProvider = Provider<NotificationsApiService>(
  (ref) => NotificationsApiService(),
);

class NotificationsNotifier
    extends StateNotifier<AsyncValue<List<NotificationModel>>> {
  NotificationsNotifier(this._ref) : super(const AsyncValue.loading()) {
    loadNotifications();
  }

  final Ref _ref;

  Future<void> loadNotifications() async {
    state = const AsyncValue.loading();
    try {
      final authService = _ref.read(authServiceProvider);
      final userId = await authService.getSavedUserId();

      if (userId == null) {
        state = AsyncValue.error(
          Exception('Пользователь не авторизован: нет сохранённого userId'),
          StackTrace.current,
        );
        return;
      }

      final api = _ref.read(notificationsApiServiceProvider);
      final items = await api.fetchNotifications(userId: userId);

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

    final authService = _ref.read(authServiceProvider);
    final userId = await authService.getSavedUserId();
    if (userId == null) return;

    try {
      final api = _ref.read(notificationsApiServiceProvider);
      await api.markAsRead(notificationId: notifId, userId: userId);

      final updated = [
        for (final n in current.value)
          if (n.id == id) n.copyWith(isRead: true) else n,
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
