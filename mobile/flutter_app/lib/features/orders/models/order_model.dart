class OrderModel {
  final int id;
  final double totalPrice;
  final String status;
  final String statusDisplay; // "In assembly", "New", etc.
  final String fulfillmentType; // "delivery" or "pickup"
  final int itemsCount; // Number of items
  final DateTime createdAt;
  final String? courierPhone; // Courier phone
  final String? pickerPhone; // Picker phone

  OrderModel({
    required this.id,
    required this.totalPrice,
    required this.status,
    required this.statusDisplay,
    required this.fulfillmentType,
    required this.itemsCount,
    required this.createdAt,
    this.courierPhone,
    this.pickerPhone,
  });

  factory OrderModel.fromJson(Map<String, dynamic> json) {
    return OrderModel(
      id: json['id'],
      // Parse price safely, it might come as a string
      totalPrice: double.tryParse(json['total_price'].toString()) ?? 0.0,
      status: json['status'] ?? '',
      statusDisplay: json['status_display'] ?? '',
      fulfillmentType: (json['fulfillment_type'] ?? 'delivery').toString(),
      itemsCount: json['items_count'] ?? 0,
      // Parse date
      createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
      courierPhone: json['courier_phone'] as String?,
      pickerPhone: json['picker_phone'] as String?,
    );
  }
}
