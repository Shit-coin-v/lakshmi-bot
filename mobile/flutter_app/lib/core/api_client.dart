import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiClient {
  static const String _baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8000',
  );

  static const String _apiKey = String.fromEnvironment(
    'API_KEY',
    defaultValue: 'my_secret_mobile_key_2025',
  );

  /// Resolves a media URL returned by the API to use the correct base URL.
  static String resolveMediaUrl(String url) {
    final path = Uri.parse(url).path;
    return '$_baseUrl$path';
  }

  static final ApiClient _instance = ApiClient._internal();

  factory ApiClient() => _instance;

  final Dio _dio = Dio(
    BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      contentType: Headers.jsonContentType,
      headers: {
        'X-Api-Key': _apiKey,
      },
    ),
  );

  static const _storage = FlutterSecureStorage();
  static const _accessTokenKey = 'auth_access_token';
  static const _refreshTokenKey = 'auth_refresh_token';

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

    // JWT refresh interceptor
    _dio.interceptors.add(
      InterceptorsWrapper(
        onError: (DioException e, handler) async {
          if (e.response?.statusCode == 401 &&
              !e.requestOptions.path.contains('/api/auth/')) {
            final refreshed = await _tryRefreshToken();
            if (refreshed) {
              // Retry the original request with new token
              final opts = e.requestOptions;
              opts.headers['Authorization'] =
                  _dio.options.headers['Authorization'];
              try {
                final response = await _dio.fetch(opts);
                return handler.resolve(response);
              } on DioException catch (retryError) {
                return handler.next(retryError);
              }
            }
          }
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

  void setBearerToken(String token) {
    _dio.options.headers['Authorization'] = 'Bearer $token';
  }

  void clearBearerToken() {
    _dio.options.headers.remove('Authorization');
  }

  /// Save tokens to secure storage and set Bearer header.
  Future<void> saveTokens(String accessToken, String refreshToken) async {
    await _storage.write(key: _accessTokenKey, value: accessToken);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
    setBearerToken(accessToken);
  }

  /// Clear tokens from storage and headers.
  Future<void> clearTokens() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
    clearBearerToken();
  }

  /// Restore Bearer token from storage (for auto-login).
  Future<String?> getSavedAccessToken() async {
    return await _storage.read(key: _accessTokenKey);
  }

  Future<String?> getSavedRefreshToken() async {
    return await _storage.read(key: _refreshTokenKey);
  }

  /// Try to refresh the access token using the stored refresh token.
  Future<bool> _tryRefreshToken() async {
    final refreshToken = await _storage.read(key: _refreshTokenKey);
    if (refreshToken == null) return false;

    try {
      final response = await Dio(BaseOptions(
        baseUrl: _baseUrl,
        headers: {'X-Api-Key': _apiKey},
      )).post('/api/auth/refresh/', data: {'refresh': refreshToken});

      if (response.statusCode == 200) {
        final tokens = response.data['tokens'];
        await saveTokens(tokens['access'], tokens['refresh']);
        return true;
      }
    } catch (e) {
      debugPrint("Token refresh failed: $e");
    }

    await clearTokens();
    return false;
  }

  Dio get dio => _dio;
}
