import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/services/auth_service.dart';
import '../features/notifications/services/push_api_service.dart';

final pushNotificationServiceProvider = Provider(
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
            AndroidFlutterLocalNotificationsPlugin>();
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
    final token = await _messaging.getToken();
    if (token != null) {
      await registerTokenForCurrentUser(token);
    }
  }

  void _listenForTokenRefresh() {
    _messaging.onTokenRefresh.listen((token) {
      registerTokenForCurrentUser(token);
    });
  }

  void _listenForMessages(GoRouter router) {
    FirebaseMessaging.onMessage.listen(_showForegroundNotification);

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
    final orderId = message.data['order_id'];
    final status = message.data['status'];

    final statusText = _statusText(status) ??
        message.notification?.body ??
        'Статус заказа обновлён';

    await _localNotifications.show(
      message.hashCode,
      'Статус заказа',
      statusText,
      NotificationDetails(
        android: AndroidNotificationDetails(
          _channel.id,
          _channel.name,
          channelDescription: _channel.description,
          importance: Importance.high,
          priority: Priority.high,
        ),
      ),
      payload: orderId,
    );
  }

  Future<void> registerTokenForCurrentUser([String? overrideToken]) async {
    final token = overrideToken ?? await _messaging.getToken();
    if (token == null || token.isEmpty) return;

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

  void _handleNavigation(GoRouter router, Map<String, dynamic> data) {
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
