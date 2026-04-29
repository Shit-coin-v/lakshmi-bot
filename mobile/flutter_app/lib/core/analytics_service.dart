import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'api_client.dart';

class AnalyticsService {
  static final AnalyticsService _instance = AnalyticsService._internal();
  factory AnalyticsService() => _instance;
  AnalyticsService._internal() : _dio = ApiClient().dio, _checkAuth = true;

  // Тестовый конструктор: позволяет инжектить Dio и пропустить проверку токена
  // (она нужна только в проде, где токен может отсутствовать в начале сессии).
  @visibleForTesting
  AnalyticsService.withDio(Dio dio)
      : _dio = dio,
        _checkAuth = false;

  final Dio _dio;
  final bool _checkAuth;

  Future<void> _track(String eventType, {String screen = '', Map<String, dynamic>? payload}) async {
    if (_checkAuth && !ApiClient().hasAccessToken) return;
    try {
      await _dio.post('/api/analytics/events/', data: {
        'event_type': eventType,
        if (screen.isNotEmpty) 'screen': screen,
        if (payload != null) 'payload': payload,
      });
    } catch (_) {
      // fire-and-forget: аналитика не должна ломать UX
    }
  }

  Future<void> trackScreenView(String screen, {Map<String, dynamic>? payload}) =>
      _track('screen_view', screen: screen, payload: payload);

  Future<void> trackCartAdd(String productId, int quantity) =>
      _track('cart_add', payload: {'product_id': productId, 'quantity': quantity});

  Future<void> trackCartRemove(String productId) =>
      _track('cart_remove', payload: {'product_id': productId});

  Future<void> trackSearch(String query, int resultsCount) =>
      _track('search', payload: {'query': query, 'results_count': resultsCount});

  Future<void> trackPromoClick(int promoId, String source) =>
      _track('promo_click', payload: {'promo_id': promoId, 'source': source});

  Future<void> trackSessionStart() => _track('session_start');

  Future<void> trackSessionEnd() => _track('session_end');

  Future<void> trackCategoryView({required int categoryId, required int depth}) =>
      _track('category_view', payload: {'category_id': categoryId, 'depth': depth});

  Future<void> trackCatalogButtonTap() => _track('catalog_button_tap');
}
