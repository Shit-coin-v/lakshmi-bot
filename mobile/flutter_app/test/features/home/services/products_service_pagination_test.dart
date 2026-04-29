import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:lakshmi_market/features/home/services/products_service.dart';

import '../../../helpers/mocks.dart';

Response<dynamic> _resp({
  required List<dynamic> body,
  Map<String, dynamic>? headers,
}) {
  return Response(
    data: body,
    statusCode: 200,
    headers: Headers.fromMap(
      (headers ?? {}).map((k, v) => MapEntry(k, [v.toString()])),
    ),
    requestOptions: RequestOptions(path: '/api/products/'),
  );
}

void main() {
  late MockDio mockDio;
  late ProductsService service;

  setUp(() {
    mockDio = MockDio();
    service = ProductsService(dio: mockDio);
  });

  group('ProductsService.getShowcase pagination', () {
    test('returns hasMore=true when Link header has rel="next"', () async {
      when(() => mockDio.get(
            '/api/showcase/',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => _resp(
            body: [],
            headers: {'link': '<http://srv/api/showcase/?page=2>; rel="next"'},
          ));

      final page = await service.getShowcase();

      expect(page.hasMore, true);
    });

    test('returns hasMore=false when no Link header', () async {
      when(() => mockDio.get(
            '/api/showcase/',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => _resp(body: []));

      final page = await service.getShowcase();

      expect(page.hasMore, false);
    });

    test('omits page query param when page=1', () async {
      when(() => mockDio.get(
            '/api/showcase/',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => _resp(body: []));

      await service.getShowcase(page: 1);

      final captured = verify(() => mockDio.get(
            '/api/showcase/',
            queryParameters: captureAny(named: 'queryParameters'),
          )).captured.single as Map<String, dynamic>;

      expect(captured.containsKey('page'), false);
    });

    test('passes page=N when page > 1', () async {
      when(() => mockDio.get(
            '/api/showcase/',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => _resp(body: []));

      await service.getShowcase(page: 3);

      final captured = verify(() => mockDio.get(
            '/api/showcase/',
            queryParameters: captureAny(named: 'queryParameters'),
          )).captured.single as Map<String, dynamic>;

      expect(captured['page'], 3);
    });
  });

  group('ProductsService.getProducts pagination', () {
    test('returns hasMore=true when Link header has rel="next"', () async {
      when(() => mockDio.get(
            '/api/products/',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => _resp(
            body: [],
            headers: {'link': '<http://srv/api/products/?page=2>; rel="next"'},
          ));

      final page = await service.getProducts(categoryId: 5);

      expect(page.hasMore, true);
    });

    test('passes category_id and page > 1', () async {
      when(() => mockDio.get(
            '/api/products/',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => _resp(body: []));

      await service.getProducts(categoryId: 7, page: 2);

      final captured = verify(() => mockDio.get(
            '/api/products/',
            queryParameters: captureAny(named: 'queryParameters'),
          )).captured.single as Map<String, dynamic>;

      expect(captured['category_id'], 7);
      expect(captured['page'], 2);
    });
  });
}
