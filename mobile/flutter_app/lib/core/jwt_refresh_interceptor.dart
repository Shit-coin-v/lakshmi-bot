import 'package:dio/dio.dart';

/// Callback that attempts to refresh the access token.
/// Returns `true` if refresh succeeded and new token is set on [dio].
typedef TokenRefresher = Future<bool> Function();

/// Callback fired when refresh fails and user must re-authenticate.
typedef ForceLogoutCallback = void Function();

/// Dio interceptor that handles JWT token refresh on 401 responses.
///
/// - 401 on non-auth path → calls [refreshToken] → retries original request
/// - 401 on `/api/auth/` path → passes through (auth endpoints handle own errors)
/// - 403 or other codes → passes through (no refresh)
class JwtRefreshInterceptor extends Interceptor {
  final Dio dio;
  final TokenRefresher refreshToken;
  final ForceLogoutCallback onForceLogout;

  JwtRefreshInterceptor({
    required this.dio,
    required this.refreshToken,
    required this.onForceLogout,
  });

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401 &&
        !err.requestOptions.path.contains('/api/auth/')) {
      final refreshed = await refreshToken();
      if (refreshed) {
        final opts = err.requestOptions;
        opts.headers['Authorization'] = dio.options.headers['Authorization'];
        try {
          final response = await dio.fetch(opts);
          return handler.resolve(response);
        } on DioException catch (retryError) {
          return handler.next(retryError);
        }
      } else {
        onForceLogout();
      }
    }
    return handler.next(err);
  }
}
