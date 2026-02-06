import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/order_model.dart';
import '../services/order_service.dart';
import '../models/order_detail_model.dart';

// Этот провайдер сам загрузит данные при открытии экрана
final myOrdersProvider = FutureProvider.autoDispose<List<OrderModel>>((
  ref,
) async {
  final service = ref.watch(orderServiceProvider);
  return service.fetchMyOrders();
});

// Провайдер для получения одного заказа по ID (family позволяет передать ID)
final orderByIdProvider = FutureProvider.family.autoDispose<OrderModel, int>((
  ref,
  id,
) async {
  final service = ref.watch(orderServiceProvider);
  return service.fetchOrderById(id);
});

final orderDetailByIdProvider = FutureProvider.family
    .autoDispose<OrderDetailModel, int>((ref, id) async {
      final service = ref.watch(orderServiceProvider);
      return service.fetchOrderDetailById(id);
    });
final repeatOrderProvider =
    Provider.autoDispose<Future<int> Function(int orderId)>((ref) {
      final service = ref.watch(orderServiceProvider);
      return (orderId) => service.repeatOrder(orderId);
    });

final cancelOrderProvider =
    Provider.autoDispose<Future<void> Function(int orderId)>((ref) {
      final service = ref.watch(orderServiceProvider);
      return (orderId) => service.cancelOrder(orderId);
    });
