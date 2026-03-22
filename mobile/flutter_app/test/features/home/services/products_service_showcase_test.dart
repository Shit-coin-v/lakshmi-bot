import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:lakshmi_market/features/home/services/products_service.dart';
import 'package:lakshmi_market/features/home/models/product.dart';

import '../../../helpers/mocks.dart';

void main() {
  late MockDio mockDio;
  late ProductsService service;

  setUp(() {
    mockDio = MockDio();
    service = ProductsService(dio: mockDio);
  });

  group('ProductsService.getShowcase', () {
    test('returns parsed list of products', () async {
      when(() => mockDio.get(
            '/api/showcase/',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => Response(
            data: [
              {
                'product_code': 'SH-001',
                'name': 'Топ товар',
                'price': '199.90',
                'image_url': '/media/top.png',
                'description': 'Хит продаж',
                'stock': 50,
              },
            ],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/showcase/'),
          ));

      final products = await service.getShowcase();

      expect(products, isA<List<Product>>());
      expect(products.length, 1);
      expect(products[0].id, 'SH-001');
      expect(products[0].name, 'Топ товар');
      expect(products[0].price, 199.90);
    });

    test('passes search parameter when non-empty', () async {
      when(() => mockDio.get(
            '/api/showcase/',
            queryParameters: {'search': 'молоко'},
          )).thenAnswer((_) async => Response(
            data: [],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/showcase/'),
          ));

      final products = await service.getShowcase(search: 'молоко');

      expect(products, isEmpty);
      verify(() => mockDio.get(
            '/api/showcase/',
            queryParameters: {'search': 'молоко'},
          )).called(1);
    });

    test('sends empty queryParameters when search is empty', () async {
      when(() => mockDio.get(
            '/api/showcase/',
            queryParameters: <String, dynamic>{},
          )).thenAnswer((_) async => Response(
            data: [],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/showcase/'),
          ));

      await service.getShowcase(search: '');

      verify(() => mockDio.get(
            '/api/showcase/',
            queryParameters: <String, dynamic>{},
          )).called(1);
    });

    test('throws Exception on Dio error', () async {
      when(() => mockDio.get(
            '/api/showcase/',
            queryParameters: any(named: 'queryParameters'),
          )).thenThrow(DioException(
            requestOptions: RequestOptions(path: '/api/showcase/'),
            type: DioExceptionType.connectionTimeout,
          ));

      expect(
        () => service.getShowcase(),
        throwsA(isA<Exception>().having(
          (e) => e.toString(),
          'message',
          contains('Ошибка загрузки витрины'),
        )),
      );
    });
  });

  group('ProductsService.getProducts with categoryId', () {
    test('passes category_id in queryParameters', () async {
      when(() => mockDio.get(
            '/api/products/',
            queryParameters: {'category_id': 5},
          )).thenAnswer((_) async => Response(
            data: [
              {
                'product_code': 'CAT-001',
                'name': 'Товар категории',
                'price': '50.00',
                'description': '',
                'stock': 10,
              },
            ],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/products/'),
          ));

      final products = await service.getProducts(categoryId: 5);

      expect(products.length, 1);
      expect(products[0].id, 'CAT-001');
      verify(() => mockDio.get(
            '/api/products/',
            queryParameters: {'category_id': 5},
          )).called(1);
    });

    test('passes both search and category_id', () async {
      when(() => mockDio.get(
            '/api/products/',
            queryParameters: {'search': 'хлеб', 'category_id': 3},
          )).thenAnswer((_) async => Response(
            data: [],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/products/'),
          ));

      final products = await service.getProducts(search: 'хлеб', categoryId: 3);

      expect(products, isEmpty);
      verify(() => mockDio.get(
            '/api/products/',
            queryParameters: {'search': 'хлеб', 'category_id': 3},
          )).called(1);
    });

    test('throws Exception on Dio error', () async {
      when(() => mockDio.get(
            '/api/products/',
            queryParameters: any(named: 'queryParameters'),
          )).thenThrow(DioException(
            requestOptions: RequestOptions(path: '/api/products/'),
            type: DioExceptionType.badResponse,
          ));

      expect(
        () => service.getProducts(categoryId: 1),
        throwsA(isA<Exception>().having(
          (e) => e.toString(),
          'message',
          contains('Ошибка загрузки товаров'),
        )),
      );
    });
  });
}
