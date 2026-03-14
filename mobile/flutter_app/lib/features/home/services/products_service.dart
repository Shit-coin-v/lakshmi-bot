import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';
import '../models/product.dart';

final productsServiceProvider = Provider((ref) => ProductsService());

class ProductsService {
  final Dio _dio;

  ProductsService({Dio? dio}) : _dio = dio ?? ApiClient().dio;

  /// Витрина главной страницы — предрассчитанный ranking + актуальный stock.
  Future<List<Product>> getShowcase({String search = ''}) async {
    try {
      final response = await _dio.get(
        '/api/showcase/',
        queryParameters: {
          if (search.isNotEmpty) 'search': search,
        },
      );

      final List<dynamic> data = response.data;
      return data.map((json) => Product.fromJson(json)).toList();
    } catch (e) {
      throw Exception('Ошибка загрузки витрины: $e');
    }
  }

  /// Каталог — товары по категории или поиск.
  Future<List<Product>> getProducts({String search = '', int? categoryId}) async {
    try {
      final response = await _dio.get(
        '/api/products/',
        queryParameters: {
          if (search.isNotEmpty) 'search': search,
          if (categoryId != null) 'category_id': categoryId,
        },
      );

      final List<dynamic> data = response.data;
      return data.map((json) => Product.fromJson(json)).toList();
    } catch (e) {
      throw Exception('Ошибка загрузки товаров: $e');
    }
  }
}
