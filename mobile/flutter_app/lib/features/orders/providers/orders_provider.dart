import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/order_model.dart';
import '../services/order_service.dart';
import '../models/order_detail_model.dart';

// This provider auto-loads data when the screen opens
final myOrdersProvider = FutureProvider.autoDispose<List<OrderModel>>((
  ref,
) async {
  final service = ref.watch(orderServiceProvider);
  return service.fetchMyOrders();
});

// Provider for fetching a single order by ID (family allows passing ID)
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
    Provider.autoDispose<Future<int> Function(int orderId, {required String paymentMethod, double? changeFrom, double? totalPrice})>((ref) {
      final service = ref.watch(orderServiceProvider);
      return (orderId, {required paymentMethod, changeFrom, totalPrice}) =>
          service.repeatOrder(orderId, paymentMethod: paymentMethod, changeFrom: changeFrom, totalPrice: totalPrice);
    });

final cancelOrderProvider =
    Provider.autoDispose<Future<void> Function(int orderId)>((ref) {
      final service = ref.watch(orderServiceProvider);
      return (orderId) => service.cancelOrder(orderId);
    });
