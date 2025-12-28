import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/services/auth_service.dart';
import '../features/notifications/providers/notifications_provider.dart';
import '../features/notifications/services/push_api_service.dart';

final pushNotificationServiceProvider = Provider<PushNotificationService>(
  (ref) => PushNotificationService(ref),
);

class PushNotificationService {
  PushNotificationService(this._ref);

  final Ref _ref;
  final FirebaseMessaging _messaging = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();
  final PushApiService _pushApi = PushApiService();

  static const AndroidNotificationChannel _channel = AndroidNotificationChannel(
    'order_status_updates',
    'Обновления заказов',
    description: 'Уведомления об изменении статуса заказа',
    importance: Importance.high,
  );

  bool _initialized = false;

  Future<void> initialize(GoRouter router) async {
    if (_initialized) return;
    _initialized = true;

    await _configureLocalNotifications(router);
    await _requestPermissions();
    await _syncCurrentToken();
    _listenForTokenRefresh();
    _listenForMessages(router);
  }

  Future<void> _configureLocalNotifications(GoRouter router) async {
    const initializationSettings = InitializationSettings(
      android: AndroidInitializationSettings('@mipmap/ic_launcher'),
    );

    await _localNotifications.initialize(
      initializationSettings,
      onDidReceiveNotificationResponse: (response) {
        final payload = response.payload;
        if (payload != null && payload.isNotEmpty) {
          _openOrderStatus(router, payload);
        }
      },
    );

    final androidPlugin = _localNotifications
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >();
    await androidPlugin?.createNotificationChannel(_channel);
  }

  Future<void> _requestPermissions() async {
    await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      carPlay: false,
      criticalAlert: false,
      provisional: false,
    );

    await _messaging.setForegroundNotificationPresentationOptions(
      alert: true,
      badge: true,
      sound: true,
    );
  }

  Future<void> _syncCurrentToken() async {
    try {
      final token = await _messaging.getToken();
      debugPrint(
        'FCM token = ${token == null ? "NULL" : "${token.substring(0, 12)}..."}',
      );

      if (token != null && token.isNotEmpty) {
        await registerTokenForCurrentUser(token);
      }
    } catch (e) {
      debugPrint('FCM token error (ignored): $e');
    }
  }

  void _listenForTokenRefresh() {
    _messaging.onTokenRefresh.listen((token) async {
      try {
        await registerTokenForCurrentUser(token);
      } catch (e) {
        debugPrint('FCM token refresh error (ignored): $e');
      }
    });
  }

  void _listenForMessages(GoRouter router) {
    FirebaseMessaging.onMessage.listen((message) {
      _showForegroundNotification(message);
    });

    FirebaseMessaging.onMessageOpenedApp.listen((message) {
      _handleNavigation(router, message.data);
    });

    _messaging.getInitialMessage().then((message) {
      if (message != null) {
        _handleNavigation(router, message.data);
      }
    });
  }

  Future<void> _showForegroundNotification(RemoteMessage message) async {
    final data = message.data;

    final orderId = data['order_id']?.toString();
    final status = data['status']?.toString();
    final notificationId = data['notification_id']?.toString();

    final title =
        message.notification?.title ??
        (orderId != null ? 'Статус заказа' : 'Уведомление');

    final body =
        message.notification?.body ??
        _statusText(status) ??
        'Новое уведомление';

    await _localNotifications.show(
      message.hashCode,
      title,
      body,
      NotificationDetails(
        android: AndroidNotificationDetails(
          _channel.id,
          _channel.name,
          channelDescription: _channel.description,
          importance: Importance.high,
          priority: Priority.high,
        ),
      ),
      payload: orderId ?? notificationId ?? '',
    );

    try {
      await _ref.read(notificationsProvider.notifier).loadNotifications();
    } catch (_) {}
  }

  Future<void> registerTokenForCurrentUser([String? overrideToken]) async {
    String? token;

    try {
      token = overrideToken ?? await _messaging.getToken();
    } catch (e) {
      debugPrint('FCM getToken error (ignored): $e');
      return;
    }

    if (token == null || token.isEmpty) return;
    debugPrint('FCM TOKEN: ${token.substring(0, 12)}...');

    final authService = _ref.read(authServiceProvider);
    final customerId = await authService.getSavedUserId();
    if (customerId == null) return;

    try {
      await _pushApi.registerToken(
        customerId: customerId,
        fcmToken: token,
        platform: 'android',
      );
    } catch (e) {
      debugPrint('Не удалось отправить FCM токен: $e');
    }
  }

  void _handleNavigation(GoRouter router, Map<String, dynamic> data) async {
    try {
      await _ref.read(notificationsProvider.notifier).loadNotifications();
    } catch (_) {}

    final orderId = data['order_id']?.toString();
    if (orderId != null && orderId.isNotEmpty) {
      _openOrderStatus(router, orderId);
    }
  }

  void _openOrderStatus(GoRouter router, String orderId) {
    router.go('/order-status/$orderId');
  }

  String? _statusText(String? status) {
    switch (status) {
      case 'assembly':
        return 'Заказ собирается';
      case 'delivery':
        return 'Курьер выехал';
      case 'completed':
        return 'Заказ доставлен';
      case 'canceled':
        return 'Заказ отменён';
      default:
        return null;
    }
  }
}
