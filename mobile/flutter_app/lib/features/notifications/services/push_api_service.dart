import 'package:dio/dio.dart';

import '../../../core/api_client.dart';

class PushApiService {
  final Dio _dio;

  PushApiService({Dio? dio}) : _dio = dio ?? ApiClient().dio;

  Future<void> registerToken({
    required String fcmToken,
    String platform = 'android',
  }) async {
    await _dio.post(
      '/api/fcm/token/',
      data: {
        'fcm_token': fcmToken,
        'platform': platform,
      },
    );
  }
}
