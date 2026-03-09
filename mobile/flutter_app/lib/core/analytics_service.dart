import 'package:dio/dio.dart';
import 'api_client.dart';

class AnalyticsService {
  static final AnalyticsService _instance = AnalyticsService._internal();
  factory AnalyticsService() => _instance;
  AnalyticsService._internal();

  final Dio _dio = ApiClient().dio;

  Future<void> _track(String eventType, {String screen = '', Map<String, dynamic>? payload}) async {
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

  Future<void> trackCartAdd(int productId, int quantity) =>
      _track('cart_add', payload: {'product_id': productId, 'quantity': quantity});

  Future<void> trackCartRemove(int productId) =>
      _track('cart_remove', payload: {'product_id': productId});

  Future<void> trackSearch(String query, int resultsCount) =>
      _track('search', payload: {'query': query, 'results_count': resultsCount});

  Future<void> trackPromoClick(int promoId, String source) =>
      _track('promo_click', payload: {'promo_id': promoId, 'source': source});

  Future<void> trackSessionStart() => _track('session_start');

  Future<void> trackSessionEnd() => _track('session_end');
}
