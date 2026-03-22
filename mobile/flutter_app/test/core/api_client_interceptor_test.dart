import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

/// Tests for the JWT refresh interceptor pattern used in ApiClient.
///
/// We recreate the exact interceptor logic from api_client.dart and test
/// it with a fake HTTP adapter, verifying:
/// 1. 401 on non-auth path → refresh → retry → success
/// 2. 403 does NOT trigger refresh
/// 3. 401 on /api/auth/ path does NOT trigger refresh
void main() {
  group('JWT refresh interceptor logic', () {
    test('401 on non-auth path triggers refresh and retries request', () async {
      var refreshCalled = false;
      var retryCalled = false;

      final dio = Dio(BaseOptions(baseUrl: 'http://fake'));

      // Replace adapter: first call → 401, refresh → 200, retry → 200
      dio.httpClientAdapter = _SequenceAdapter([
        // 1st: POST /api/orders/create/ → 401
        (options) => _error(options, 401, {'detail': 'expired'}),
        // 2nd: POST /api/auth/refresh/ → 200 with tokens
        (options) => _success(options, 200, {
              'tokens': {'access': 'new-access', 'refresh': 'new-refresh'}
            }),
        // 3rd: retry POST /api/orders/create/ → 201
        (options) => _success(options, 201, {'id': 42}),
      ]);

      // Add interceptor matching ApiClient pattern
      dio.interceptors.add(InterceptorsWrapper(
        onError: (DioException e, handler) async {
          if (e.response?.statusCode == 401 &&
              !e.requestOptions.path.contains('/api/auth/')) {
            refreshCalled = true;
            try {
              final refreshResp =
                  await dio.post('/api/auth/refresh/', data: {});
              if (refreshResp.statusCode == 200) {
                retryCalled = true;
                final opts = e.requestOptions;
                opts.headers['Authorization'] = 'Bearer new-access';
                final retryResp = await dio.fetch(opts);
                return handler.resolve(retryResp);
              }
            } catch (_) {}
          }
          return handler.next(e);
        },
      ));

      final response = await dio.post('/api/orders/create/', data: {});

      expect(refreshCalled, isTrue, reason: '401 should trigger refresh');
      expect(retryCalled, isTrue, reason: 'After refresh, should retry');
      expect(response.statusCode, 201);
    });

    test('403 does NOT trigger refresh flow', () async {
      var refreshCalled = false;

      final dio = Dio(BaseOptions(baseUrl: 'http://fake'));

      dio.httpClientAdapter = _SequenceAdapter([
        (options) => _error(options, 403, {'detail': 'forbidden'}),
      ]);

      dio.interceptors.add(InterceptorsWrapper(
        onError: (DioException e, handler) async {
          if (e.response?.statusCode == 401 &&
              !e.requestOptions.path.contains('/api/auth/')) {
            refreshCalled = true;
          }
          return handler.next(e);
        },
      ));

      try {
        await dio.post('/api/orders/create/', data: {});
        fail('Should have thrown');
      } on DioException catch (e) {
        expect(e.response?.statusCode, 403);
      }

      expect(refreshCalled, isFalse,
          reason: '403 should NOT trigger refresh');
    });

    test('401 on /api/auth/ path does NOT trigger refresh', () async {
      var refreshCalled = false;

      final dio = Dio(BaseOptions(baseUrl: 'http://fake'));

      dio.httpClientAdapter = _SequenceAdapter([
        (options) => _error(options, 401, {'detail': 'bad credentials'}),
      ]);

      dio.interceptors.add(InterceptorsWrapper(
        onError: (DioException e, handler) async {
          if (e.response?.statusCode == 401 &&
              !e.requestOptions.path.contains('/api/auth/')) {
            refreshCalled = true;
          }
          return handler.next(e);
        },
      ));

      try {
        await dio.post('/api/auth/login/', data: {});
        fail('Should have thrown');
      } on DioException catch (e) {
        expect(e.response?.statusCode, 401);
      }

      expect(refreshCalled, isFalse,
          reason: '401 on auth path should NOT trigger refresh');
    });
  });
}

// --- Helpers ---

typedef _ResponseFactory = Future<ResponseBody> Function(RequestOptions);

/// Adapter that returns responses in sequence.
class _SequenceAdapter implements HttpClientAdapter {
  final List<_ResponseFactory> _factories;
  int _index = 0;

  _SequenceAdapter(this._factories);

  @override
  Future<ResponseBody> fetch(RequestOptions options,
      Stream<List<int>>? requestStream, Future<void>? cancelFuture) async {
    if (_index >= _factories.length) {
      throw StateError(
          'No more fake responses (call #${_index + 1}, '
          'path=${options.path})');
    }
    return _factories[_index++](options);
  }

  @override
  void close({bool force = false}) {}
}

Future<ResponseBody> _success(
    RequestOptions options, int statusCode, Map<String, dynamic> data) async {
  return ResponseBody.fromString(
    jsonEncode(data),
    statusCode,
    headers: {
      'content-type': ['application/json; charset=utf-8'],
    },
  );
}

Future<ResponseBody> _error(
    RequestOptions options, int statusCode, Map<String, dynamic> data) async {
  throw DioException(
    requestOptions: options,
    response: Response(
      requestOptions: options,
      statusCode: statusCode,
      data: data,
    ),
    type: DioExceptionType.badResponse,
  );
}
