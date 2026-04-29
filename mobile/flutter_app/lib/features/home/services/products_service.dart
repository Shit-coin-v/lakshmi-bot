import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';
import '../models/product.dart';

final productsServiceProvider = Provider((ref) => ProductsService());

/// Результат запроса страницы товаров.
class ProductPage {
  final List<Product> items;
  final bool hasMore;

  const ProductPage({required this.items, required this.hasMore});
}

class ProductsService {
  final Dio _dio;

  ProductsService({Dio? dio}) : _dio = dio ?? ApiClient().dio;

  /// Витрина главной страницы — предрассчитанный ranking + актуальный stock.
  Future<ProductPage> getShowcase({String search = '', int page = 1}) async {
    try {
      final response = await _dio.get(
        '/api/showcase/',
        queryParameters: {
          if (search.isNotEmpty) 'search': search,
          if (page > 1) 'page': page,
        },
      );
      return _toProductPage(response);
    } catch (e) {
      throw Exception('Ошибка загрузки витрины: $e');
    }
  }

  /// Каталог — товары по категории или поиск.
  Future<ProductPage> getProducts({
    String search = '',
    int? categoryId,
    int page = 1,
  }) async {
    try {
      final response = await _dio.get(
        '/api/products/',
        queryParameters: {
          if (search.isNotEmpty) 'search': search,
          if (categoryId != null) 'category_id': categoryId,
          if (page > 1) 'page': page,
        },
      );
      return _toProductPage(response);
    } catch (e) {
      throw Exception('Ошибка загрузки товаров: $e');
    }
  }

  ProductPage _toProductPage(Response<dynamic> response) {
    final List<dynamic> data = response.data as List<dynamic>;
    final items = data
        .map((json) => Product.fromJson(json as Map<String, dynamic>))
        .toList();
    final hasMore = _hasNextLink(response.headers);
    return ProductPage(items: items, hasMore: hasMore);
  }

  /// Парсит заголовок Link в формате RFC 5988:
  ///   `<...>; rel="next", <...>; rel="prev"`
  /// Возвращает true, если присутствует `rel="next"`.
  bool _hasNextLink(Headers headers) {
    final linkValues = headers['link'];
    if (linkValues == null || linkValues.isEmpty) return false;
    return linkValues.any((v) => v.contains('rel="next"'));
  }
}
