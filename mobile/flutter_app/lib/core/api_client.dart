import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

class ApiClient {
  static const String _baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8000',
  );

  static const String _apiKey = String.fromEnvironment(
    'API_KEY',
    defaultValue: 'my_secret_mobile_key_2025',
  );

  static final ApiClient _instance = ApiClient._internal();

  factory ApiClient() => _instance;

  final Dio _dio = Dio(
    BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      headers: {
        'Content-Type': 'application/json',
        // Заголовок для Django
        'X-Api-Key': _apiKey,
      },
    ),
  );

  ApiClient._internal() {
    debugPrint("API_CLIENT baseUrl=$_baseUrl apiKey=$_apiKey");
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          debugPrint(
            "REQUEST[${options.method}] => URL: ${options.uri}",
          );
          return handler.next(options);
        },
        onError: (DioException e, handler) {
          debugPrint(
            "ERROR[${e.response?.statusCode}] => PATH: ${e.requestOptions.path}",
          );
          debugPrint("Message: ${e.response?.data}");
          debugPrint("Type: ${e.type}");
          debugPrint("Error: ${e.message}");
          debugPrint("URL: ${e.requestOptions.uri}");
          return handler.next(e);
        },
      ),
    );
  }

  void setTelegramUserId(int telegramId) {
    _dio.options.headers['X-Telegram-User-Id'] =
        telegramId.toString();
  }

  void clearTelegramUserId() {
    _dio.options.headers.remove('X-Telegram-User-Id');
  }

  Dio get dio => _dio;
}

    
