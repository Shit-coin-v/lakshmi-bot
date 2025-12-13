import 'package:dio/dio.dart';

import '../../../core/api_client.dart';

class PushApiService {
  final Dio _dio = ApiClient().dio;

  Future<void> registerToken({
    required int customerId,
    required String fcmToken,
    String platform = 'android',
  }) async {
    await _dio.post(
      '/api/push/register/',
      data: {
        'customer_id': customerId,
        'fcm_token': fcmToken,
        'platform': platform,
      },
    );
  }
}
