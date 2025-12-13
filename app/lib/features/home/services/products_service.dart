import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';
import '../models/product.dart';

final productsServiceProvider = Provider((ref) => ProductsService());

class ProductsService {
  final Dio _dio = ApiClient().dio;

  ProductsService();

  Future<List<Product>> getProducts({String search = ''}) async {
    try {
      final response = await _dio.get(
        '/api/products/',
        // 👇 Добавляем параметр поиска, если он не пустой
        queryParameters: {if (search.isNotEmpty) 'search': search},
      );

      final List<dynamic> data = response.data;
      // Используем fromJson из класса Product
      return data.map((json) => Product.fromJson(json)).toList();
    } catch (e) {
      throw Exception('Ошибка загрузки товаров: $e');
    }
  }
}
