import 'dart:async';

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
    defaultValue: '',
  );

  static const String botUsername = String.fromEnvironment(
    'BOT_USERNAME',
    defaultValue: '',
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

  Completer<bool>? _refreshCompleter;

  final StreamController<void> _onForceLogout =
      StreamController<void>.broadcast();
  Stream<void> get onForceLogout => _onForceLogout.stream;

  ApiClient._internal() {
    assert(_apiKey.isNotEmpty, 'API_KEY must be provided via --dart-define');
    assert(botUsername.isNotEmpty, 'BOT_USERNAME must be provided via --dart-define');

    if (kDebugMode) {
      debugPrint("API_CLIENT baseUrl=$_baseUrl");
    }

    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          if (kDebugMode) {
            debugPrint(
              "REQUEST[${options.method}] => URL: ${options.uri}",
            );
          }
          return handler.next(options);
        },
        onError: (DioException e, handler) {
          if (kDebugMode) {
            debugPrint(
              "ERROR[${e.response?.statusCode}] => PATH: ${e.requestOptions.path}",
            );
            debugPrint("Type: ${e.type}");
            debugPrint("Error: ${e.message}");
          }
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
            } else {
              _onForceLogout.add(null);
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
  /// Uses Completer-based mutex to prevent concurrent refresh attempts.
  Future<bool> _tryRefreshToken() async {
    if (_refreshCompleter != null) {
      return _refreshCompleter!.future;
    }

    _refreshCompleter = Completer<bool>();
    try {
      final refreshToken = await _storage.read(key: _refreshTokenKey);
      if (refreshToken == null) {
        _refreshCompleter!.complete(false);
        return false;
      }

      final response = await Dio(BaseOptions(
        baseUrl: _baseUrl,
        headers: {'X-Api-Key': _apiKey},
      )).post('/api/auth/refresh/', data: {'refresh': refreshToken});

      if (response.statusCode == 200) {
        final tokens = response.data['tokens'];
        await saveTokens(tokens['access'], tokens['refresh']);
        _refreshCompleter!.complete(true);
        return true;
      }

      await clearTokens();
      _refreshCompleter!.complete(false);
      return false;
    } catch (e) {
      if (kDebugMode) debugPrint("Token refresh failed: $e");
      await clearTokens();
      _refreshCompleter!.complete(false);
      return false;
    } finally {
      _refreshCompleter = null;
    }
  }

  Dio get dio => _dio;
}
