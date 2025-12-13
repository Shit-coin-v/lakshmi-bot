import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';
import '../../auth/services/auth_service.dart';
import '../models/order_model.dart';
import '../models/order_detail_model.dart';

final orderServiceProvider = Provider((ref) => OrderService(ref));

class OrderService {
  final Ref _ref;
  final Dio _dio = ApiClient().dio;

  OrderService(this._ref);

  // Получить список всех заказов
  Future<List<OrderModel>> fetchMyOrders() async {
    try {
      final authService = _ref.read(authServiceProvider);
      final userId = await authService.getSavedUserId();

      if (userId == null) throw Exception('Пользователь не авторизован');

      final response = await _dio.get(
        '/api/orders/',
        queryParameters: {'user_id': userId},
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = response.data;
        return data.map((json) => OrderModel.fromJson(json)).toList();
      } else {
        throw Exception('Ошибка: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Ошибка загрузки списка: $e');
    }
  }

  // Получить ОДИН заказ по ID (Этого метода могло не быть)
  Future<OrderModel> fetchOrderById(int id) async {
    try {
      final response = await _dio.get('/api/orders/$id/');

      if (response.statusCode == 200) {
        return OrderModel.fromJson(response.data);
      } else {
        throw Exception('Заказ не найден');
      }
    } catch (e) {
      throw Exception('Ошибка загрузки заказа: $e');
    }
  }

  Future<OrderDetailModel> fetchOrderDetailById(int id) async {
    try {
      final response = await _dio.get('/api/orders/$id/');

      if (response.statusCode == 200) {
        return OrderDetailModel.fromJson(response.data);
      } else {
        throw Exception('Заказ не найден');
      }
    } catch (e) {
      throw Exception('Ошибка загрузки деталей заказа: $e');
    }
  }
}
