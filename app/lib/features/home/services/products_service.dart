import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/constants/api_constants.dart';
import '../models/product.dart';

// Простой провайдер, который выдает этот сервис
final productsServiceProvider = Provider((ref) => ProductsService());

class ProductsService {
  final Dio _dio = Dio();

  Future<List<Product>> fetchProducts() async {
    try {
      final response = await _dio.get(
        '${ApiConstants.baseUrl}${ApiConstants.productsPath}',
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = response.data;
        // Превращаем список JSON в список объектов Product
        return data.map((json) => Product.fromJson(json)).toList();
      } else {
        throw Exception('Ошибка сервера: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Не удалось загрузить товары: $e');
    }
  }
}
