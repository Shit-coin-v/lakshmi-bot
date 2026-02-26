import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';
import '../models/product.dart';

final productsServiceProvider = Provider((ref) => ProductsService());

class ProductsService {
  final Dio _dio;

  ProductsService({Dio? dio}) : _dio = dio ?? ApiClient().dio;

  Future<List<Product>> getProducts({String search = ''}) async {
    try {
      final response = await _dio.get(
        '/api/products/',
        // Add search param if not empty
        queryParameters: {if (search.isNotEmpty) 'search': search},
      );

      final List<dynamic> data = response.data;
      // Use Product.fromJson
      return data.map((json) => Product.fromJson(json)).toList();
    } catch (e) {
      throw Exception('Ошибка загрузки товаров: $e');
    }
  }
}
