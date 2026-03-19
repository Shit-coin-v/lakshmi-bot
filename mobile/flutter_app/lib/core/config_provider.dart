import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'api_client.dart';

class DeliveryZone {
  final String name;
  final String productCode;
  final double price;
  final bool isDefault;

  DeliveryZone({
    required this.name,
    required this.productCode,
    required this.price,
    required this.isDefault,
  });

  factory DeliveryZone.fromJson(Map<String, dynamic> json) {
    return DeliveryZone(
      name: json['name'] ?? '',
      productCode: json['product_code'] ?? '',
      price: double.parse(json['price'].toString()),
      isDefault: json['is_default'] == true,
    );
  }
}

final deliveryZonesProvider = FutureProvider.autoDispose<List<DeliveryZone>>((ref) async {
  final response = await ApiClient().dio.get('/api/config/');
  final List zones = response.data['delivery_zones'] ?? [];
  return zones.map((z) => DeliveryZone.fromJson(z)).toList();
});
