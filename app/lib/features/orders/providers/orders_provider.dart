import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/order_model.dart';
import '../services/order_service.dart';

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
