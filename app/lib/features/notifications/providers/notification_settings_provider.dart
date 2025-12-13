import 'package:flutter_riverpod/flutter_riverpod.dart';

// Модель настроек
class NotificationSettings {
  final bool pushOrders; // Статусы заказов
  final bool pushPromos; // Акции и скидки
  final bool news; // Новости магазина (НОВОЕ)

  NotificationSettings({
    this.pushOrders = true,
    this.pushPromos = true,
    this.news = true,
  });

  NotificationSettings copyWith({
    bool? pushOrders,
    bool? pushPromos,
    bool? news,
  }) {
    return NotificationSettings(
      pushOrders: pushOrders ?? this.pushOrders,
      pushPromos: pushPromos ?? this.pushPromos,
      news: news ?? this.news,
    );
  }
}

// Провайдер управления
class NotificationSettingsNotifier extends StateNotifier<NotificationSettings> {
  NotificationSettingsNotifier() : super(NotificationSettings());

  void togglePushOrders(bool value) {
    state = state.copyWith(pushOrders: value);
  }

  void togglePushPromos(bool value) {
    state = state.copyWith(pushPromos: value);
  }

  void toggleNews(bool value) {
    state = state.copyWith(news: value);
  }
}

final notificationSettingsProvider =
    StateNotifierProvider<NotificationSettingsNotifier, NotificationSettings>((
      ref,
    ) {
      return NotificationSettingsNotifier();
    });
