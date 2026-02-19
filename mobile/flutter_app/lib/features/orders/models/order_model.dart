class OrderModel {
  final int id;
  final double totalPrice;
  final String status;
  final String statusDisplay; // "В сборке", "Новый" и т.д.
  final String fulfillmentType; // "delivery" или "pickup"
  final int itemsCount; // Количество товаров
  final DateTime createdAt;
  final String? courierPhone; // Телефон курьера
  final String? pickerPhone; // Телефон сборщика

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
      // Парсим цену аккуратно, вдруг придет строка
      totalPrice: double.tryParse(json['total_price'].toString()) ?? 0.0,
      status: json['status'] ?? '',
      statusDisplay: json['status_display'] ?? '',
      fulfillmentType: (json['fulfillment_type'] ?? 'delivery').toString(),
      itemsCount: json['items_count'] ?? 0,
      // Парсим дату
      createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
      courierPhone: json['courier_phone'] as String?,
      pickerPhone: json['picker_phone'] as String?,
    );
  }
}
