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

  group('ProductsService', () {
    test('getProducts returns parsed list of products', () async {
      when(() => mockDio.get(
            '/api/products/',
            queryParameters: any(named: 'queryParameters'),
          )).thenAnswer((_) async => Response(
            data: [
              {
                'product_code': 'ABC-001',
                'name': 'Молоко',
                'price': '89.90',
                'image_url': '/media/milk.png',
                'description': 'Свежее молоко',
                'stock': 10,
              },
              {
                'product_code': 'ABC-002',
                'name': 'Хлеб',
                'price': '45.00',
                'image_url': null,
                'description': 'Белый хлеб',
                'stock': 25,
              },
            ],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/products/'),
          ));

      final products = await service.getProducts();

      expect(products, isA<List<Product>>());
      expect(products.length, 2);
      expect(products[0].id, 'ABC-001');
      expect(products[0].name, 'Молоко');
      expect(products[0].price, 89.90);
      expect(products[0].stock, 10);
      expect(products[1].id, 'ABC-002');
      expect(products[1].name, 'Хлеб');
      expect(products[1].price, 45.00);
    });

    test('getProducts with search passes query parameter', () async {
      when(() => mockDio.get(
            '/api/products/',
            queryParameters: {'search': 'молоко'},
          )).thenAnswer((_) async => Response(
            data: [
              {
                'product_code': 'ABC-001',
                'name': 'Молоко',
                'price': '89.90',
                'description': 'Свежее молоко',
                'stock': 10,
              },
            ],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/products/'),
          ));

      final products = await service.getProducts(search: 'молоко');

      expect(products.length, 1);
      expect(products[0].name, 'Молоко');
      verify(() => mockDio.get(
            '/api/products/',
            queryParameters: {'search': 'молоко'},
          )).called(1);
    });

    test('getProducts with empty search sends no query params', () async {
      when(() => mockDio.get(
            '/api/products/',
            queryParameters: <String, dynamic>{},
          )).thenAnswer((_) async => Response(
            data: [],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/products/'),
          ));

      final products = await service.getProducts(search: '');

      expect(products, isEmpty);
      verify(() => mockDio.get(
            '/api/products/',
            queryParameters: <String, dynamic>{},
          )).called(1);
    });

    test('getProducts on Dio error throws Exception', () async {
      when(() => mockDio.get(
            '/api/products/',
            queryParameters: any(named: 'queryParameters'),
          )).thenThrow(DioException(
            requestOptions: RequestOptions(path: '/api/products/'),
            type: DioExceptionType.connectionTimeout,
          ));

      expect(
        () => service.getProducts(),
        throwsA(isA<Exception>().having(
          (e) => e.toString(),
          'message',
          contains('Ошибка загрузки товаров'),
        )),
      );
    });
  });
}
