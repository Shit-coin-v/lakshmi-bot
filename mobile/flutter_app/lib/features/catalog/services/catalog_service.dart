import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_client.dart';
import '../models/category_node.dart';

final catalogServiceProvider = Provider((ref) => CatalogService());

class CatalogService {
  final Dio _dio;

  CatalogService({Dio? dio}) : _dio = dio ?? ApiClient().dio;

  Future<List<CategoryNode>> getRootCategories() async {
    try {
      final response = await _dio.get('/api/catalog/root/');
      final List<dynamic> data = response.data;
      return data.map((json) => CategoryNode.fromJson(json)).toList();
    } catch (e) {
      throw Exception('Ошибка загрузки категорий: $e');
    }
  }

  Future<List<CategoryNode>> getChildren(int parentId) async {
    try {
      final response = await _dio.get('/api/catalog/$parentId/children/');
      final List<dynamic> data = response.data;
      return data.map((json) => CategoryNode.fromJson(json)).toList();
    } catch (e) {
      throw Exception('Ошибка загрузки подкатегорий: $e');
    }
  }
}
