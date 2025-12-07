import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';
import '../models/cart_item.dart';

final orderServiceProvider = Provider((ref) => OrderService());

class OrderService {
  final Dio _dio = ApiClient().dio;

  Future<int?> createOrder({
    required String address,
    required String phone,
    required String comment,
    required double totalPrice,
    required List<CartItem> items,
    required int userId,
  }) async {
    try {
      final itemsJson = items
          .map(
            (item) => {
              "product_id": item.product.id,
              "quantity": item.quantity,
              "price_at_moment": item.product.price,
            },
          )
          .toList();

      final response = await _dio.post(
        '/api/orders/create/',
        data: {
          "customer": userId,
          "address": address,
          "phone": phone,
          "comment": comment,
          "total_price": totalPrice,
          "items": itemsJson,
        },
      );

      if (response.statusCode == 201) {
        return response.data['id'];
      }
      return null;
    } catch (e) {
      return null;
    }
  }
}
