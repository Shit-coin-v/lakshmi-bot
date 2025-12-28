class OrderModel {
  final int id;
  final double totalPrice;
  final String status;
  final String statusDisplay; // "В сборке", "Новый" и т.д.
  final int itemsCount; // Количество товаров
  final DateTime createdAt;

  OrderModel({
    required this.id,
    required this.totalPrice,
    required this.status,
    required this.statusDisplay,
    required this.itemsCount,
    required this.createdAt,
  });

  factory OrderModel.fromJson(Map<String, dynamic> json) {
    return OrderModel(
      id: json['id'],
      // Парсим цену аккуратно, вдруг придет строка
      totalPrice: double.tryParse(json['total_price'].toString()) ?? 0.0,
      status: json['status'] ?? '',
      statusDisplay: json['status_display'] ?? '',
      itemsCount: json['items_count'] ?? 0,
      // Парсим дату
      createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
    );
  }
}
