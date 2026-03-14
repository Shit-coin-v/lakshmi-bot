import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';
import '../models/product.dart';

final productsServiceProvider = Provider((ref) => ProductsService());

class ProductsService {
  final Dio _dio;

  ProductsService({Dio? dio}) : _dio = dio ?? ApiClient().dio;

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
      // Use Product.fromJson
      return data.map((json) => Product.fromJson(json)).toList();
    } catch (e) {
      throw Exception('Ошибка загрузки товаров: $e');
    }
  }
}
