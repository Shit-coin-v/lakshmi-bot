import 'package:dio/dio.dart';

import '../../../core/api_client.dart';
import '../models/notification_model.dart';

class NotificationsApiService {
  final Dio _dio;

  NotificationsApiService({Dio? dio}) : _dio = dio ?? ApiClient().dio;

  Future<List<NotificationModel>> fetchNotifications() async {
    final response = await _dio.get('/api/notifications/');

    final data = response.data;
    if (data is! List) return [];

    return data
        .whereType<Map<String, dynamic>>()
        .map(NotificationModel.fromJson)
        .toList();
  }

  Future<void> markAsRead({
    required int notificationId,
    String source = 'inapp',
  }) async {
    await _dio.post(
      '/api/notifications/$notificationId/read/',
      data: {'source': source},
    );
  }
}
