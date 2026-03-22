import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:lakshmi_market/features/catalog/services/catalog_service.dart';
import 'package:lakshmi_market/features/catalog/models/category_node.dart';

import '../../../helpers/mocks.dart';

void main() {
  late MockDio mockDio;
  late CatalogService service;

  setUp(() {
    mockDio = MockDio();
    service = CatalogService(dio: mockDio);
  });

  group('CatalogService', () {
    group('getRootCategories', () {
      test('returns parsed list of CategoryNode', () async {
        when(() => mockDio.get('/api/catalog/root/')).thenAnswer(
          (_) async => Response(
            data: [
              {
                'id': 1,
                'name': 'Молочные продукты',
                'parent_id': null,
                'has_children': true,
              },
              {
                'id': 2,
                'name': 'Хлеб',
                'parent_id': null,
                'has_children': false,
              },
            ],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/catalog/root/'),
          ),
        );

        final categories = await service.getRootCategories();

        expect(categories, isA<List<CategoryNode>>());
        expect(categories.length, 2);
        expect(categories[0].id, 1);
        expect(categories[0].name, 'Молочные продукты');
        expect(categories[0].parentId, isNull);
        expect(categories[0].hasChildren, true);
        expect(categories[0].isLeaf, false);
        expect(categories[1].id, 2);
        expect(categories[1].name, 'Хлеб');
        expect(categories[1].hasChildren, false);
        expect(categories[1].isLeaf, true);
      });

      test('returns empty list when server returns empty array', () async {
        when(() => mockDio.get('/api/catalog/root/')).thenAnswer(
          (_) async => Response(
            data: [],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/catalog/root/'),
          ),
        );

        final categories = await service.getRootCategories();

        expect(categories, isEmpty);
      });

      test('throws Exception on Dio error', () async {
        when(() => mockDio.get('/api/catalog/root/')).thenThrow(
          DioException(
            requestOptions: RequestOptions(path: '/api/catalog/root/'),
            type: DioExceptionType.connectionTimeout,
          ),
        );

        expect(
          () => service.getRootCategories(),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('Ошибка загрузки категорий'),
          )),
        );
      });
    });

    group('getChildren', () {
      test('returns parsed list of child categories', () async {
        when(() => mockDio.get('/api/catalog/1/children/')).thenAnswer(
          (_) async => Response(
            data: [
              {
                'id': 10,
                'name': 'Молоко',
                'parent_id': 1,
                'has_children': false,
              },
              {
                'id': 11,
                'name': 'Кефир',
                'parent_id': 1,
                'has_children': false,
              },
            ],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/catalog/1/children/'),
          ),
        );

        final children = await service.getChildren(1);

        expect(children, isA<List<CategoryNode>>());
        expect(children.length, 2);
        expect(children[0].id, 10);
        expect(children[0].name, 'Молоко');
        expect(children[0].parentId, 1);
        expect(children[1].id, 11);
        expect(children[1].name, 'Кефир');
      });

      test('returns empty list for leaf category', () async {
        when(() => mockDio.get('/api/catalog/5/children/')).thenAnswer(
          (_) async => Response(
            data: [],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/catalog/5/children/'),
          ),
        );

        final children = await service.getChildren(5);

        expect(children, isEmpty);
      });

      test('throws Exception on Dio error', () async {
        when(() => mockDio.get('/api/catalog/1/children/')).thenThrow(
          DioException(
            requestOptions:
                RequestOptions(path: '/api/catalog/1/children/'),
            type: DioExceptionType.badResponse,
            response: Response(
              statusCode: 500,
              requestOptions:
                  RequestOptions(path: '/api/catalog/1/children/'),
            ),
          ),
        );

        expect(
          () => service.getChildren(1),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('Ошибка загрузки подкатегорий'),
          )),
        );
      });
    });
  });
}
