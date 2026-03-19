import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'api_client.dart';

final deliveryPriceProvider = FutureProvider.autoDispose<double>((ref) async {
  final response = await ApiClient().dio.get('/api/config/');
  return double.parse(response.data['delivery_price'].toString());
});
