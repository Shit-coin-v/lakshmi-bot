import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';
import '../../orders/models/order_model.dart';
import '../models/cart_item.dart';

final orderServiceProvider = Provider((ref) => OrderService(ref));

class OrderService {
  final Dio _dio;

  OrderService(Ref ref, {Dio? dio}) : _dio = dio ?? ApiClient().dio;

  // Получить список всех заказов
  Future<List<OrderModel>> fetchMyOrders() async {
    try {
      final response = await _dio.get('/api/orders/');

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

  // Получить ОДИН заказ по ID
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

  Future<int?> createOrder({
    required String address,
    required String phone,
    required String comment,
    required String paymentMethod,
    required double totalPrice,
    required List<CartItem> items,
    required int userId,
    String fulfillmentType = "delivery",
  }) async {
    try {
      final ft = (fulfillmentType.trim().isEmpty)
          ? "delivery"
          : fulfillmentType.trim();
      // Валидация: проверяем что у всех товаров есть product_code
      for (final item in items) {
        if (item.product.id.isEmpty) {
          throw Exception('Товар "${item.product.name}" не имеет кода');
        }
      }

      final orderData = {
        "customer": userId,
        "address": address,
        "phone": phone,
        "comment": comment,
        "payment_method": paymentMethod,
        "fulfillment_type": ft,
        "total_price": double.parse(totalPrice.toStringAsFixed(2)),
        "items": items
            .map(
              (item) => {
                "product_code": item.product.id,
                "quantity": item.quantity,
                "price_at_moment": double.parse(item.product.price.toStringAsFixed(2)),
              },
            )
            .toList(),
      };

      final response = await _dio.post('/api/orders/create/', data: orderData);

      if (response.statusCode == 201) {
        return response.data['id'];
      }
      return null;
    } on DioException {
      rethrow;
    } catch (e) {
      throw Exception('Ошибка создания заказа: $e');
    }
  }
}
