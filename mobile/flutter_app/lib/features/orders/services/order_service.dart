import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api_client.dart';
import '../models/order_detail_model.dart';
import '../models/order_model.dart';

final orderServiceProvider = Provider((ref) => OrderService(ref));

class OrderService {
  final Ref _ref;
  final Dio _dio;

  OrderService(this._ref, {Dio? dio}) : _dio = dio ?? ApiClient().dio;

  Future<List<OrderModel>> fetchMyOrders() async {
    try {
      final response = await _dio.get('/api/orders/');

      if (response.statusCode == 200) {
        final List<dynamic> data = response.data as List<dynamic>;
        return data
            .map((json) => OrderModel.fromJson(json as Map<String, dynamic>))
            .toList();
      }

      throw Exception('Ошибка: ${response.statusCode}');
    } catch (e) {
      throw Exception('Ошибка загрузки списка: $e');
    }
  }

  Future<OrderModel> fetchOrderById(int id) async {
    try {
      final response = await _dio.get('/api/orders/$id/');

      if (response.statusCode == 200) {
        return OrderModel.fromJson(response.data as Map<String, dynamic>);
      }

      throw Exception('Заказ не найден');
    } catch (e) {
      throw Exception('Ошибка загрузки заказа: $e');
    }
  }

  Future<OrderDetailModel> fetchOrderDetailById(int id) async {
    try {
      final response = await _dio.get('/api/orders/$id/');

      if (response.statusCode == 200) {
        return OrderDetailModel.fromJson(response.data as Map<String, dynamic>);
      }

      throw Exception('Заказ не найден');
    } catch (e) {
      throw Exception('Ошибка загрузки деталей заказа: $e');
    }
  }

  Future<int> repeatOrder(
    int orderId, {
    required String paymentMethod,
    double? changeFrom,
  }) async {
    try {
      final detailRes = await _dio.get('/api/orders/$orderId/');
      if (detailRes.statusCode != 200) {
        throw Exception('Не удалось получить заказ №$orderId');
      }

      final Map<String, dynamic> o = Map<String, dynamic>.from(detailRes.data);

      final String phone = (o['phone'] ?? '').toString();
      final String oldComment = (o['comment'] ?? '').toString();

      final String addressRaw = (o['address'] ?? '').toString().trim();

      String fulfillmentType = (o['fulfillment_type'] ?? '').toString().trim();

      if (fulfillmentType.isEmpty) {
        fulfillmentType = addressRaw.toLowerCase() == 'самовывоз'
            ? 'pickup'
            : 'delivery';
      }

      final String address = fulfillmentType == 'pickup'
          ? 'Самовывоз'
          : addressRaw;

      final List<dynamic> orderItems = (o['items'] as List<dynamic>? ?? []);
      if (orderItems.isEmpty) {
        throw Exception('В заказе нет товаров — повторить нечего');
      }

      final List<Map<String, dynamic>> itemsPayload = orderItems.map((it) {
        final m = Map<String, dynamic>.from(it as Map);

        final code = (m['product_code'] ?? '').toString();
        final qtyRaw = m['quantity'];
        final priceRaw = m['price_at_moment'];

        if (code.isEmpty) {
          throw Exception('В одном из items отсутствует product_code');
        }

        final int quantity = qtyRaw is int
            ? qtyRaw
            : int.parse(qtyRaw.toString());
        final double price = double.tryParse(priceRaw.toString()) ?? 0.0;

        return {
          'product_code': code,
          'quantity': quantity,
          'price_at_moment': price.toStringAsFixed(2),
        };
      }).toList();

      String commentText = 'Повтор заказа №$orderId. $oldComment'.trim();
      if (changeFrom != null) {
        commentText += ' Сдача с ${changeFrom.toInt()} ₽';
      }

      final payload = {
        'fulfillment_type': fulfillmentType,
        'address': address,
        'phone': phone,
        'comment': commentText,
        'payment_method': paymentMethod,
        'items': itemsPayload,
      };

      final createRes = await _dio.post('/api/orders/create/', data: payload);

      if (createRes.statusCode != 201 && createRes.statusCode != 200) {
        throw Exception('Не удалось создать повтор заказа');
      }

      final Map<String, dynamic> created = Map<String, dynamic>.from(
        createRes.data,
      );

      final newIdRaw = created['id'];
      if (newIdRaw == null) throw Exception('В ответе нет id нового заказа');

      return newIdRaw is int ? newIdRaw : int.parse(newIdRaw.toString());
    } catch (e) {
      throw Exception('Ошибка повтора заказа: $e');
    }
  }

  Future<void> cancelOrder(int orderId) async {
    try {
      final response = await _dio.post('/api/orders/$orderId/cancel/');
      if (response.statusCode != 200) {
        final detail = response.data?['detail'] ?? 'Неизвестная ошибка';
        throw Exception(detail);
      }
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Ошибка отмены заказа';
      throw Exception(detail);
    }
  }
}
