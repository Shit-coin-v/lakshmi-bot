import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:lakshmi_market/core/analytics_service.dart';

import '../helpers/mocks.dart';

class _AnyResponse extends Fake implements Response<dynamic> {}

void main() {
  setUpAll(() {
    registerFallbackValue(_AnyResponse());
  });

  late MockDio mockDio;
  late AnalyticsService service;

  setUp(() {
    mockDio = MockDio();
    when(() => mockDio.post(any(), data: any(named: 'data')))
        .thenAnswer((_) async => Response(
              data: {},
              statusCode: 201,
              requestOptions: RequestOptions(path: '/api/analytics/events/'),
            ));
    service = AnalyticsService.withDio(mockDio);
  });

  group('AnalyticsService new events', () {
    test('trackCategoryView posts category_view with category_id and depth',
        () async {
      await service.trackCategoryView(categoryId: 42, depth: 2);

      final captured = verify(
        () => mockDio.post('/api/analytics/events/', data: captureAny(named: 'data')),
      ).captured.single as Map<String, dynamic>;

      expect(captured['event_type'], 'category_view');
      expect(captured['payload'], {'category_id': 42, 'depth': 2});
    });

    test('trackCatalogButtonTap posts catalog_button_tap with no payload',
        () async {
      await service.trackCatalogButtonTap();

      final captured = verify(
        () => mockDio.post('/api/analytics/events/', data: captureAny(named: 'data')),
      ).captured.single as Map<String, dynamic>;

      expect(captured['event_type'], 'catalog_button_tap');
      expect(captured.containsKey('payload'), false);
    });
  });
}
