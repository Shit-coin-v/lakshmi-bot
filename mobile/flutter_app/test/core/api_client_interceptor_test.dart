import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lakshmi_market/core/jwt_refresh_interceptor.dart';

/// Tests for the production [JwtRefreshInterceptor] class.
///
/// This tests the real interceptor code used by ApiClient, not a copy.
void main() {
  group('JwtRefreshInterceptor (production class)', () {
    late Dio dio;
    late _SequenceAdapter adapter;
    late bool refreshCalled;
    late bool forceLogoutCalled;
    late String? tokenAfterRefresh;

    setUp(() {
      refreshCalled = false;
      forceLogoutCalled = false;
      tokenAfterRefresh = null;

      dio = Dio(BaseOptions(baseUrl: 'http://fake'));

      dio.interceptors.add(
        JwtRefreshInterceptor(
          dio: dio,
          refreshToken: () async {
            refreshCalled = true;
            // Simulate successful refresh: set new token on dio
            tokenAfterRefresh = 'refreshed-access-token';
            dio.options.headers['Authorization'] =
                'Bearer $tokenAfterRefresh';
            return true;
          },
          onForceLogout: () {
            forceLogoutCalled = true;
          },
        ),
      );
    });

    test('401 on customer endpoint → refresh → retry with new token', () async {
      adapter = _SequenceAdapter([
        // 1st: POST /api/orders/create/ → 401
        (opts) => _throw(opts, 401),
        // 2nd: retry after refresh → 201
        (opts) => _ok(opts, 201, {'id': 42}),
      ]);
      dio.httpClientAdapter = adapter;

      final response = await dio.post('/api/orders/create/', data: {});

      expect(refreshCalled, isTrue);
      expect(forceLogoutCalled, isFalse);
      expect(response.statusCode, 201);
      expect(response.data['id'], 42);

      // Verify new token was set on retried request
      final retryOpts = adapter.capturedOptions[1];
      expect(retryOpts.headers['Authorization'],
          'Bearer refreshed-access-token');
    });

    test('403 does NOT trigger refresh', () async {
      adapter = _SequenceAdapter([
        (opts) => _throw(opts, 403),
      ]);
      dio.httpClientAdapter = adapter;

      try {
        await dio.post('/api/orders/create/', data: {});
        fail('Should have thrown');
      } on DioException catch (e) {
        expect(e.response?.statusCode, 403);
      }

      expect(refreshCalled, isFalse);
      expect(forceLogoutCalled, isFalse);
    });

    test('401 on /api/auth/ path does NOT trigger refresh', () async {
      adapter = _SequenceAdapter([
        (opts) => _throw(opts, 401),
      ]);
      dio.httpClientAdapter = adapter;

      try {
        await dio.post('/api/auth/login/', data: {});
        fail('Should have thrown');
      } on DioException catch (e) {
        expect(e.response?.statusCode, 401);
      }

      expect(refreshCalled, isFalse);
      expect(forceLogoutCalled, isFalse);
    });

    test('401 + failed refresh → force logout', () async {
      // Override interceptor with failing refresh
      dio.interceptors.clear();
      dio.interceptors.add(
        JwtRefreshInterceptor(
          dio: dio,
          refreshToken: () async {
            refreshCalled = true;
            return false; // refresh failed
          },
          onForceLogout: () {
            forceLogoutCalled = true;
          },
        ),
      );

      adapter = _SequenceAdapter([
        (opts) => _throw(opts, 401),
      ]);
      dio.httpClientAdapter = adapter;

      try {
        await dio.get('/api/customer/me/bonus-history/');
        fail('Should have thrown');
      } on DioException catch (e) {
        expect(e.response?.statusCode, 401);
      }

      expect(refreshCalled, isTrue);
      expect(forceLogoutCalled, isTrue);
    });
  });
}

// --- Test helpers ---

typedef _ResponseFactory = Future<ResponseBody> Function(RequestOptions);

class _SequenceAdapter implements HttpClientAdapter {
  final List<_ResponseFactory> _factories;
  int _index = 0;
  final List<RequestOptions> capturedOptions = [];

  _SequenceAdapter(this._factories);

  @override
  Future<ResponseBody> fetch(RequestOptions options,
      Stream<List<int>>? requestStream, Future<void>? cancelFuture) async {
    capturedOptions.add(options);
    if (_index >= _factories.length) {
      throw StateError('No more fake responses (call #${_index + 1})');
    }
    return _factories[_index++](options);
  }

  @override
  void close({bool force = false}) {}
}

Future<ResponseBody> _ok(
    RequestOptions opts, int code, Map<String, dynamic> data) async {
  return ResponseBody.fromString(
    jsonEncode(data),
    code,
    headers: {
      'content-type': ['application/json; charset=utf-8'],
    },
  );
}

Future<ResponseBody> _throw(RequestOptions opts, int code) async {
  throw DioException(
    requestOptions: opts,
    response: Response(requestOptions: opts, statusCode: code, data: {}),
    type: DioExceptionType.badResponse,
  );
}
