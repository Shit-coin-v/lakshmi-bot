import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/notification_model.dart';

class NotificationsNotifier extends StateNotifier<List<NotificationModel>> {
  NotificationsNotifier() : super([]) {
    loadNotifications();
  }

  Future<void> loadNotifications() async {
    // Имитация задержки сети
    await Future.delayed(const Duration(milliseconds: 500));

    state = [
      NotificationModel(
        id: '1',
        title: 'Заказ #12345 собран',
        body:
            'Ваш заказ готов к передаче курьеру. Ожидайте доставку в течение часа.',
        date: DateTime.now().subtract(const Duration(minutes: 15)),
        isRead: false,
        type: 'order',
      ),
      NotificationModel(
        id: '2',
        title: 'Скидка 20% на фрукты',
        body:
            'Только сегодня! Успейте заказать свежие фрукты со скидкой. Акция действует до 22:00.',
        date: DateTime.now().subtract(const Duration(days: 1)),
        isRead: true,
        type: 'promo',
      ),
      NotificationModel(
        id: '3',
        title: 'Добро пожаловать!',
        body:
            'Рады видеть вас в Lakshmi Market. Ваш QR-код для скидок уже готов.',
        date: DateTime.now().subtract(const Duration(days: 5)),
        isRead: true,
        type: 'system',
      ),
    ];
  }

  void markAsRead(String id) {
    state = [
      for (final notification in state)
        if (notification.id == id)
          notification.copyWith(isRead: true)
        else
          notification,
    ];
  }

  void clearAll() {
    state = [];
  }
}

final notificationsProvider =
    StateNotifierProvider<NotificationsNotifier, List<NotificationModel>>((
      ref,
    ) {
      return NotificationsNotifier();
    });
