class OrderItemDetailModel {
  final String productCode;
  final String name;
  final int quantity;
  final double priceAtMoment;

  OrderItemDetailModel({
    required this.productCode,
    required this.name,
    required this.quantity,
    required this.priceAtMoment,
  });

  factory OrderItemDetailModel.fromJson(Map<String, dynamic> json) {
    return OrderItemDetailModel(
      productCode: (json['product_code'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      quantity: int.tryParse(json['quantity'].toString()) ?? 0,
      priceAtMoment: double.tryParse(json['price_at_moment'].toString()) ?? 0.0,
    );
  }
}

class OrderDetailModel {
  final int id;
  final DateTime createdAt;

  final String status;
  final String statusDisplay;

  final String paymentMethod;
  final String address;
  final String phone;
  final String comment;

  final double productsPrice;
  final double deliveryPrice;
  final double totalPrice;

  final List<OrderItemDetailModel> items;

  OrderDetailModel({
    required this.id,
    required this.createdAt,
    required this.status,
    required this.statusDisplay,
    required this.paymentMethod,
    required this.address,
    required this.phone,
    required this.comment,
    required this.productsPrice,
    required this.deliveryPrice,
    required this.totalPrice,
    required this.items,
  });

  factory OrderDetailModel.fromJson(Map<String, dynamic> json) {
    final itemsRaw = (json['items'] as List?) ?? const [];

    return OrderDetailModel(
      id: int.tryParse(json['id'].toString()) ?? 0,
      createdAt:
          DateTime.tryParse((json['created_at'] ?? '').toString()) ??
          DateTime.now(),
      status: (json['status'] ?? '').toString(),
      statusDisplay: (json['status_display'] ?? '').toString(),
      paymentMethod: (json['payment_method'] ?? '').toString(),
      address: (json['address'] ?? '').toString(),
      phone: (json['phone'] ?? '').toString(),
      comment: (json['comment'] ?? '').toString(),
      productsPrice: double.tryParse(json['products_price'].toString()) ?? 0.0,
      deliveryPrice: double.tryParse(json['delivery_price'].toString()) ?? 0.0,
      totalPrice: double.tryParse(json['total_price'].toString()) ?? 0.0,
      items: itemsRaw
          .whereType<Map>()
          .map(
            (e) => OrderItemDetailModel.fromJson(Map<String, dynamic>.from(e)),
          )
          .toList(),
    );
  }
}
